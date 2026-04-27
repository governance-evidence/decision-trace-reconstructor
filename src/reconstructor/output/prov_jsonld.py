"""W3C PROV-O JSON-LD writer for the reconstruction artifacts.

This module turns the flat result objects into provenance graphs that speak the
W3C PROV vocabulary. The public functions remain here; implementation details
live in focused context, identifier, and node-builder modules.
"""

from __future__ import annotations

from typing import Any

from ..mapping.feasibility import PropertyFeasibility
from ..pipeline import ReconstructionReport
from ..synthetic.generator import Scenario
from .prov_context import CONTEXT, DEMM_NS, PROV_NS, SCHEMA_NS
from .prov_identifiers import _agent_iri, _chain_iri
from .prov_nodes import _agent_node, _chain_node, _fragment_node, _unit_node


def chain_to_jsonld(
    scenario: Scenario,
    report: ReconstructionReport,
    chain_feas: list[PropertyFeasibility],
) -> dict[str, Any]:
    """Emit a full PROV-O JSON-LD document for a single reconstructed chain.

    The graph contains:
      - one ``demm:DecisionChain`` (subtype of ``prov:Collection``)
      - one ``demm:DecisionUnit`` per decision unit (subtype of ``prov:Activity``)
      - one ``demm:Fragment`` per source fragment (subtype of ``prov:Entity``)
      - one ``prov:Agent`` per distinct actor
      - per-property feasibility records reified as ``demm:PropertyFeasibility``
    """
    sid = scenario.scenario_id
    actors: dict[str, dict[str, Any]] = {}
    for f in report.chain.source_fragments:
        actors.setdefault(f.actor_id, _agent_node(sid, f.actor_id))

    units = [_unit_node(sid, u) for u in report.chain.units]
    fragments = [_fragment_node(sid, f) for f in report.chain.source_fragments]

    return {
        "@context": CONTEXT,
        "@graph": [
            _chain_node(scenario, report, chain_feas),
            *units,
            *fragments,
            *actors.values(),
        ],
    }


def chains_to_jsonld_bundle(
    items: list[tuple[Scenario, ReconstructionReport, list[PropertyFeasibility]]],
) -> dict[str, Any]:
    """Emit a single JSON-LD document containing many reconstructed chains.

    Used for ``named_incidents.jsonld`` -- groups all incidents into one
    governance bundle while preserving per-chain identity through IRIs.
    """
    graph: list[dict[str, Any]] = []
    seen_agents: set[str] = set()
    for scenario, report, chain_feas in items:
        sid = scenario.scenario_id
        graph.append(_chain_node(scenario, report, chain_feas))
        for unit in report.chain.units:
            graph.append(_unit_node(sid, unit))
        for f in report.chain.source_fragments:
            graph.append(_fragment_node(sid, f))
            agent_iri = _agent_iri(sid, f.actor_id)
            if agent_iri not in seen_agents:
                graph.append(_agent_node(sid, f.actor_id))
                seen_agents.add(agent_iri)
    return {"@context": CONTEXT, "@graph": graph}


def per_scenario_summary_to_jsonld(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap the flat ``per_scenario.json`` rows in a summary-level PROV-O graph."""
    graph = []
    for row in rows:
        sid = row["scenario_id"]
        graph.append(
            {
                "@id": _chain_iri(sid),
                "@type": ["prov:Collection", "DecisionChain"],
                "demm:scenarioId": sid,
                "architecture": row["architecture"],
                "stackTier": row["stack_tier"],
                "demm:seed": row["seed"],
                "demm:fragmentCount": row["fragments"],
                "demm:unitsDetected": row["units_detected"],
                "completeness": row["completeness"],
                "demm:boundaryF1": row["boundary_f1"],
                "demm:unrecoverableModeCount": row["unrecoverable_mode_count"],
                "dominantMode": row["dominant_mode"],
                "dominantBreak": row["dominant_break"],
            }
        )
    return {"@context": CONTEXT, "@graph": graph}


def cells_to_jsonld(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap ``cells.json`` aggregate-cell rows in a PROV-O summary graph."""
    graph = []
    for row in rows:
        cell_iri = f"results:cells#{row['architecture']}/{row['stack_tier']}"
        graph.append(
            {
                "@id": cell_iri,
                "@type": "demm:CellAggregate",
                "architecture": row["architecture"],
                "stackTier": row["stack_tier"],
                "demm:n": row["n"],
                "completenessPct": row["completeness_pct"],
                "demm:completenessCiLow": row["completeness_ci_low"],
                "demm:completenessCiHigh": row["completeness_ci_high"],
                "demm:boundaryF1": row["boundary_f1"],
                "demm:modalMode": row["modal_mode"],
                "demm:modalModeShare": row["modal_mode_share"],
                "dominantBreak": row["dominant_break"],
            }
        )
    return {"@context": CONTEXT, "@graph": graph}


__all__ = [
    "CONTEXT",
    "SCHEMA_NS",
    "DEMM_NS",
    "PROV_NS",
    "cells_to_jsonld",
    "chain_to_jsonld",
    "chains_to_jsonld_bundle",
    "per_scenario_summary_to_jsonld",
]
