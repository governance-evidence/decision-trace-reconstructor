"""Pin the worked Replit example to its expected outputs.

Loads ``examples/replit_drop_database/input/fragments.json`` from disk,
runs the reconstruction pipeline, and asserts every output artifact is
bit-identical to the corresponding reference under ``expected_output/``.

A failure here is a regression: either the pipeline behaviour changed
or the reference outputs need to be refreshed via
``python examples/replit_drop_database/run.py --out
examples/replit_drop_database/expected_output``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "replit_drop_database"


def _load_run_module():
    """Import the example's run.py without polluting the import cache."""
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        import run  # type: ignore[import-not-found]

        return run
    finally:
        sys.path.pop(0)


def test_replit_example_reproduces_expected_output(tmp_path: Path) -> None:
    run = _load_run_module()
    manifest = run.FragmentManifest.from_json(EXAMPLE_DIR / "input" / "fragments.json")

    from reconstructor.mapping.feasibility import FeasibilityCategory
    from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
    from reconstructor.output.prov_jsonld import chain_to_jsonld
    from reconstructor.pipeline import reconstruct
    from reconstructor.synthetic.generator import Scenario

    report = reconstruct(
        fragments=manifest.fragments,
        architecture=manifest.architecture,
        stack_tier=manifest.stack_tier,
        chain_id=manifest.scenario_id,
    )
    chain_feas = map_chain_to_schema_aggregate(
        report.chain, manifest.architecture, manifest.stack_tier
    )

    feas_payload = {
        "scenario_id": manifest.scenario_id,
        "architecture": manifest.architecture,
        "stack_tier": manifest.stack_tier.value,
        "fragments": len(manifest.fragments),
        "units_detected": len(report.chain.units),
        "completeness_pct": round(report.completeness * 100, 1),
        "dominant_mode": (report.dominant_mode().value if report.dominant_mode() else None),
        "dominant_break": (report.dominant_break().value if report.dominant_break() else None),
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

    scenario = Scenario(
        scenario_id=manifest.scenario_id,
        architecture=manifest.architecture,
        stack_tier=manifest.stack_tier,
        seed=-1,
        fragments=manifest.fragments,
        ground_truth_boundaries=[],
    )
    trace = chain_to_jsonld(scenario, report, chain_feas)
    expected_trace = json.loads((EXAMPLE_DIR / "expected_output" / "trace.jsonld").read_text())
    assert trace == expected_trace

    summary = run.build_summary(
        manifest.scenario_id,
        manifest.architecture,
        manifest.stack_tier.value,
        feas_payload,
        chain_feas,
    )
    expected_summary = (EXAMPLE_DIR / "expected_output" / "summary.txt").read_text()
    assert summary == expected_summary


def test_fragment_round_trip_through_dict() -> None:
    """Fragment.to_dict <-> Fragment.from_dict is symmetric and lossless."""
    run = _load_run_module()
    manifest = run.FragmentManifest.from_json(EXAMPLE_DIR / "input" / "fragments.json")
    for original in manifest.fragments:
        from reconstructor.core.fragment import Fragment

        round_tripped = Fragment.from_dict(original.to_dict())
        assert round_tripped == original
