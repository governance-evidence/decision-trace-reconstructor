"""Pin the Pydantic AI worked example to its expected outputs."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.adapters.pydantic_ai import (
    PydanticAIIngestOptions,
    load_runs_file,
    runs_to_manifest,
)
from reconstructor.core.fragment import Fragment, StackTier
from reconstructor.mapping.feasibility import FeasibilityCategory
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.output.prov_jsonld import chain_to_jsonld
from reconstructor.pipeline import reconstruct
from reconstructor.synthetic.generator import Scenario

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "pydantic_ai_basic_agent"


def _ingest_options() -> PydanticAIIngestOptions:
    return PydanticAIIngestOptions(
        cross_stack_tools_pattern=r"search_.*",
        takeover_tool_pattern=r"request_.*",
        human_approval_pattern=r"APPROVED",
    )


def test_pydantic_ai_ingest_produces_expected_manifest() -> None:
    runs = load_runs_file(EXAMPLE_DIR / "input" / "runs.jsonl")
    manifest = runs_to_manifest(
        runs,
        scenario_id="pydantic_ai_basic_agent_demo",
        opts=_ingest_options(),
    )
    expected = json.loads((EXAMPLE_DIR / "expected_output" / "fragments.json").read_text())
    assert manifest == expected


def test_pydantic_ai_example_reconstructs_to_expected_feasibility() -> None:
    runs = load_runs_file(EXAMPLE_DIR / "input" / "runs.jsonl")
    manifest = runs_to_manifest(
        runs,
        scenario_id="pydantic_ai_basic_agent_demo",
        opts=_ingest_options(),
    )
    fragments = [Fragment.from_dict(fragment) for fragment in manifest["fragments"]]
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
            cat.value: sum(1 for item in chain_feas if item.category == cat)
            for cat in FeasibilityCategory
        },
        "per_property": [
            {
                "property": item.property_name,
                "category": item.category.value,
                "gap": item.gap_description,
            }
            for item in chain_feas
        ],
    }

    expected = json.loads((EXAMPLE_DIR / "expected_output" / "feasibility.json").read_text())
    assert feas_payload == expected


def test_pydantic_ai_example_emits_expected_prov_jsonld() -> None:
    runs = load_runs_file(EXAMPLE_DIR / "input" / "runs.jsonl")
    manifest = runs_to_manifest(
        runs,
        scenario_id="pydantic_ai_basic_agent_demo",
        opts=_ingest_options(),
    )
    fragments = [Fragment.from_dict(fragment) for fragment in manifest["fragments"]]
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
    expected = json.loads((EXAMPLE_DIR / "expected_output" / "trace.jsonld").read_text())
    assert trace == expected
