"""Pin the Generic JSONL worked example to its expected outputs."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.adapters.generic_jsonl import (
    GenericJsonlIngestOptions,
    iter_records_file,
    load_mapping_file,
    records_to_manifest,
)
from reconstructor.core.fragment import Fragment, StackTier
from reconstructor.mapping.feasibility import FeasibilityCategory
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.output.prov_jsonld import chain_to_jsonld
from reconstructor.pipeline import reconstruct
from reconstructor.synthetic.generator import Scenario

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "generic_jsonl_basic_agent"


def _ingest_options() -> GenericJsonlIngestOptions:
    return GenericJsonlIngestOptions(redact_fields=("metadata.session_token",))


def test_generic_jsonl_ingest_produces_expected_manifest() -> None:
    mapping = load_mapping_file(EXAMPLE_DIR / "input" / "mapping.yaml")
    records = iter_records_file(EXAMPLE_DIR / "input" / "agent_log.jsonl")
    manifest = records_to_manifest(
        records,
        mapping,
        scenario_id="generic_jsonl_basic_agent_demo",
        opts=_ingest_options(),
    )
    expected = json.loads((EXAMPLE_DIR / "expected_output" / "fragments.json").read_text())
    assert manifest == expected


def test_generic_jsonl_example_reconstructs_to_expected_feasibility() -> None:
    mapping = load_mapping_file(EXAMPLE_DIR / "input" / "mapping.yaml")
    records = iter_records_file(EXAMPLE_DIR / "input" / "agent_log.jsonl")
    manifest = records_to_manifest(
        records,
        mapping,
        scenario_id="generic_jsonl_basic_agent_demo",
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


def test_generic_jsonl_example_emits_expected_prov_jsonld() -> None:
    mapping = load_mapping_file(EXAMPLE_DIR / "input" / "mapping.yaml")
    records = iter_records_file(EXAMPLE_DIR / "input" / "agent_log.jsonl")
    manifest = records_to_manifest(
        records,
        mapping,
        scenario_id="generic_jsonl_basic_agent_demo",
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
