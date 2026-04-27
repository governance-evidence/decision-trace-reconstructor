"""PROV-O JSON-LD emission tests.

Validates that the JSON-LD documents emitted by ``output.prov_jsonld``:

1. Parse as RDF graphs via ``rdflib`` (offline, using inlined context).
2. Carry the expected PROV-O typing (``prov:Activity`` / ``prov:Entity`` /
   ``prov:Agent``) for the named-incident bundle.
3. Carry the expected DEMM typing (``demm:DecisionChain``,
   ``demm:DecisionUnit``, ``demm:Fragment``, ``demm:PropertyFeasibility``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import RDF, Dataset, Namespace
from rdflib.namespace import PROV

DEMM = Namespace("https://decisiontrace.org/demm/v1#")
RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"
pytestmark = [
    pytest.mark.filterwarnings(
        r"ignore:ConjunctiveGraph is deprecated, use Dataset instead\.:DeprecationWarning"
    ),
    pytest.mark.filterwarnings(
        r"ignore:Dataset\.default_context is deprecated, use Dataset\.default_graph instead\.:DeprecationWarning"
    ),
]


def _load(filename: str) -> Dataset:
    dataset = Dataset()
    dataset.parse(RESULTS_DIR / filename, format="json-ld")
    return dataset


def test_named_incidents_jsonld_has_full_prov_graph() -> None:
    g = _load("named_incidents.jsonld")
    n_activities = sum(1 for _ in g.subjects(RDF.type, PROV.Activity))
    n_entities = sum(1 for _ in g.subjects(RDF.type, PROV.Entity))
    n_agents = sum(1 for _ in g.subjects(RDF.type, PROV.Agent))
    n_chains = sum(1 for _ in g.subjects(RDF.type, DEMM.DecisionChain))
    n_units = sum(1 for _ in g.subjects(RDF.type, DEMM.DecisionUnit))
    n_frags = sum(1 for _ in g.subjects(RDF.type, DEMM.Fragment))
    n_feas = sum(1 for _ in g.subjects(RDF.type, DEMM.PropertyFeasibility))

    # At least one of each PROV-O class should be present.
    assert n_activities > 0
    assert n_entities > 0
    assert n_agents > 0
    # DEMM classes must mirror PROV-O numbers (subtypes).
    assert n_chains > 0
    assert n_units == n_activities
    assert n_frags == n_entities
    assert n_feas > 0


def test_per_scenario_jsonld_has_summary_chains() -> None:
    g = _load("per_scenario.jsonld")
    n_chains = sum(1 for _ in g.subjects(RDF.type, DEMM.DecisionChain))
    assert n_chains > 0
    raw = json.loads((RESULTS_DIR / "per_scenario.json").read_text())
    assert n_chains == len(raw)


def test_cells_jsonld_has_one_node_per_cell() -> None:
    g = _load("cells.jsonld")
    raw = json.loads((RESULTS_DIR / "cells.json").read_text())
    n_cells = sum(1 for _ in g.subjects(RDF.type, DEMM.CellAggregate))
    assert n_cells == len(raw)


def test_chains_to_jsonld_bundle_deduplicates_agents() -> None:
    from reconstructor.core.architecture import Architecture
    from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
    from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
    from reconstructor.output.prov_jsonld import chains_to_jsonld_bundle
    from reconstructor.pipeline import reconstruct
    from reconstructor.synthetic.generator import Scenario

    scenario = Scenario(
        scenario_id="bundle_case",
        architecture=Architecture.SINGLE_AGENT,
        stack_tier=StackTier.WITHIN_STACK,
        seed=1,
        fragments=[
            Fragment(
                fragment_id="f1",
                timestamp=1.0,
                kind=FragmentKind.AGENT_MESSAGE,
                stack_tier=StackTier.WITHIN_STACK,
                actor_id="agent",
                payload={"content": "hello"},
            ),
            Fragment(
                fragment_id="f2",
                timestamp=2.0,
                kind=FragmentKind.TOOL_CALL,
                stack_tier=StackTier.WITHIN_STACK,
                actor_id="agent",
                payload={"tool_name": "write"},
            ),
        ],
        ground_truth_boundaries=[],
    )
    report = reconstruct(
        scenario.fragments,
        architecture=scenario.architecture,
        stack_tier=scenario.stack_tier,
        chain_id=scenario.scenario_id,
    )
    feasibility = map_chain_to_schema_aggregate(
        report.chain,
        scenario.architecture,
        scenario.stack_tier,
    )

    bundle = chains_to_jsonld_bundle([(scenario, report, feasibility)])

    graph = bundle["@graph"]
    assert sum(1 for node in graph if "prov:Agent" in node.get("@type", [])) == 1
    assert any("DecisionChain" in node.get("@type", []) for node in graph)
    assert any("Fragment" in node.get("@type", []) for node in graph)
