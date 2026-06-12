"""Pin the vendored OEP generic-jsonl contract to its expected feasibility output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reconstructor.adapters.generic_jsonl import (
    GenericJsonlIngestOptions,
    iter_records_file,
    load_mapping_file,
    records_to_manifest,
)
from reconstructor.core.fragment import Fragment, StackTier
from reconstructor.mapping.feasibility import FeasibilityCategory
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.pipeline import reconstruct

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "oep_code_review_agent"
SCENARIO_ID = "oep_code_review_agent"


def _manifest() -> dict[str, Any]:
    mapping = load_mapping_file(EXAMPLE_DIR / "input" / "mapping.v0.yaml")
    records = iter_records_file(EXAMPLE_DIR / "input" / "code_review_agent.jsonl")
    return records_to_manifest(
        records,
        mapping,
        scenario_id=SCENARIO_ID,
        opts=GenericJsonlIngestOptions(),
    )


def test_oep_mapping_declares_supported_schema_version() -> None:
    mapping = load_mapping_file(EXAMPLE_DIR / "input" / "mapping.v0.yaml")
    assert mapping.schema_version == "1.0"


def test_oep_example_reconstructs_to_expected_feasibility() -> None:
    manifest = _manifest()
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
