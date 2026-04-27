"""Pin the LangSmith worked example to its expected outputs.

Loads ``examples/langsmith_basic_agent/input/runs.json``, runs it through the
adapter and the reconstruction pipeline, and asserts every output artifact is
bit-identical to the corresponding reference under ``expected_output/``.

A failure here is a regression: either the adapter mapping changed, the
pipeline behaviour changed, or the reference outputs need to be refreshed.
"""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.adapters.langsmith import (
    LangSmithIngestOptions,
    runs_to_manifest,
)
from reconstructor.core.fragment import Fragment, StackTier
from reconstructor.mapping.feasibility import FeasibilityCategory
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.output.prov_jsonld import chain_to_jsonld
from reconstructor.pipeline import reconstruct
from reconstructor.synthetic.generator import Scenario

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "langsmith_basic_agent"


def _ingest_options() -> LangSmithIngestOptions:
    """Match the README's invocation parameters exactly."""
    return LangSmithIngestOptions(
        architecture="human_in_the_loop",
        stack_tier=StackTier.WITHIN_STACK,
        state_mutation_tool_pattern=r"(archive|drop|delete|exec|push|publish)",
    )


def test_langsmith_ingest_produces_expected_manifest() -> None:
    runs = json.loads((EXAMPLE_DIR / "input" / "runs.json").read_text())["runs"]
    manifest = runs_to_manifest(
        runs,
        scenario_id="langsmith_basic_agent_demo",
        opts=_ingest_options(),
    )
    expected = json.loads((EXAMPLE_DIR / "expected_output" / "fragments.json").read_text())
    assert manifest == expected


def test_langsmith_example_reconstructs_to_expected_feasibility() -> None:
    runs = json.loads((EXAMPLE_DIR / "input" / "runs.json").read_text())["runs"]
    manifest = runs_to_manifest(
        runs,
        scenario_id="langsmith_basic_agent_demo",
        opts=_ingest_options(),
    )
    fragments = [Fragment.from_dict(f) for f in manifest["fragments"]]
    tier = StackTier(manifest["stack_tier"])

    report = reconstruct(
        fragments=fragments,
        architecture=manifest["architecture"],
        stack_tier=tier,
        chain_id=manifest["scenario_id"],
    )
    chain_feas = map_chain_to_schema_aggregate(report.chain, manifest["architecture"], tier)

    feas_payload = {
        "scenario_id": manifest["scenario_id"],
        "architecture": manifest["architecture"],
        "stack_tier": tier.value,
        "fragments": len(fragments),
        "units_detected": len(report.chain.units),
        "completeness_pct": round(report.completeness * 100, 1),
        "dominant_mode": (_dm.value if (_dm := report.dominant_mode()) is not None else None),
        "dominant_break": (_db.value if (_db := report.dominant_break()) is not None else None),
        "feasibility_counts": {
            cat.value: sum(1 for f in chain_feas if f.category == cat)
            for cat in FeasibilityCategory
        },
        "per_property": [
            {
                "property": f.property_name,
                "category": f.category.value,
                "gap": f.gap_description,
            }
            for f in chain_feas
        ],
    }

    expected_feas = json.loads((EXAMPLE_DIR / "expected_output" / "feasibility.json").read_text())
    assert feas_payload == expected_feas


def test_langsmith_example_emits_expected_prov_jsonld() -> None:
    runs = json.loads((EXAMPLE_DIR / "input" / "runs.json").read_text())["runs"]
    manifest = runs_to_manifest(
        runs,
        scenario_id="langsmith_basic_agent_demo",
        opts=_ingest_options(),
    )
    fragments = [Fragment.from_dict(f) for f in manifest["fragments"]]
    tier = StackTier(manifest["stack_tier"])

    report = reconstruct(
        fragments=fragments,
        architecture=manifest["architecture"],
        stack_tier=tier,
        chain_id=manifest["scenario_id"],
    )
    chain_feas = map_chain_to_schema_aggregate(report.chain, manifest["architecture"], tier)

    scenario = Scenario(
        scenario_id=manifest["scenario_id"],
        architecture=manifest["architecture"],
        stack_tier=tier,
        seed=-1,
        fragments=fragments,
        ground_truth_boundaries=[],
    )
    trace = chain_to_jsonld(scenario, report, chain_feas)
    expected_trace = json.loads((EXAMPLE_DIR / "expected_output" / "trace.jsonld").read_text())
    assert trace == expected_trace
