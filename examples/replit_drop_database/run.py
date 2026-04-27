"""End-to-end reconstruction example: Replit DROP DATABASE incident.

Loads the fragment manifest from ``input/fragments.json``, runs the six-stage
reconstruction pipeline, and emits three artifacts to a chosen output directory:

- ``feasibility.json`` -- per-decision-event-property feasibility report
- ``trace.jsonld``     -- W3C PROV-O JSON-LD trace (full Activity/Entity/Agent graph)
- ``summary.txt``      -- human-readable summary

Run from the example directory::

    cd examples/replit_drop_database
    python run.py
    diff -ru expected_output out

If the diff is empty, your environment reproduces the reference outputs
bit-identically. The ``expected_output/`` directory ships with the package
so the example is verifiable without re-running.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconstructor.core.architecture import Architecture, coerce_architecture
from reconstructor.core.manifest import FragmentManifest
from reconstructor.mapping.feasibility import FeasibilityCategory
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.output.prov_jsonld import chain_to_jsonld
from reconstructor.pipeline import reconstruct
from reconstructor.synthetic.generator import Scenario


def build_summary(
    scenario_id: str,
    arch: Architecture | str,
    tier: str,
    feas_payload: dict,
    chain_feas: list,
) -> str:
    arch_label = coerce_architecture(arch).value
    lines = [
        "Reconstruction Summary",
        "=" * 60,
        f"Scenario:       {scenario_id}",
        f"Architecture:   {arch_label}",
        f"Stack tier:     {tier}",
        f"Fragments in:   {feas_payload['fragments']}",
        f"Units detected: {feas_payload['units_detected']}",
        f"Completeness:   {feas_payload['completeness_pct']}%",
        f"Dominant mode:  {feas_payload['dominant_mode']}",
        f"Dominant break: {feas_payload['dominant_break']}",
        "",
        "Per-decision-event-property feasibility (chain level)",
        "-" * 60,
    ]
    prop_w = max(len(f.property_name) for f in chain_feas)
    cat_w = max(len(f.category.value) for f in chain_feas)
    for f in chain_feas:
        gap = f" -- {f.gap_description}" if f.gap_description else ""
        lines.append(f"  {f.property_name:<{prop_w}}  {f.category.value:<{cat_w}}{gap}")
    nonzero = ", ".join(f"{k}={v}" for k, v in feas_payload["feasibility_counts"].items() if v)
    lines.append("")
    lines.append(f"Feasibility counts: {nonzero}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parent / "input" / "fragments.json",
        help="Fragment manifest JSON (default: ./input/fragments.json).",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "out",
        help="Output directory for reconstruction artifacts (default: ./out).",
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    manifest = FragmentManifest.from_json(args.input)
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
        "architecture": manifest.architecture.value,
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

    (args.out / "feasibility.json").write_text(json.dumps(feas_payload, indent=2) + "\n")

    # PROV-O JSON-LD requires a Scenario object; rebuild a minimal one.
    scenario = Scenario(
        scenario_id=manifest.scenario_id,
        architecture=manifest.architecture,
        stack_tier=manifest.stack_tier,
        seed=-1,
        fragments=manifest.fragments,
        ground_truth_boundaries=[],
    )
    (args.out / "trace.jsonld").write_text(
        json.dumps(chain_to_jsonld(scenario, report, chain_feas), indent=2) + "\n"
    )

    (args.out / "summary.txt").write_text(
        build_summary(
            manifest.scenario_id,
            manifest.architecture.value,
            manifest.stack_tier.value,
            feas_payload,
            chain_feas,
        )
    )

    print(f"Reconstructed {manifest.scenario_id}")
    print(f"  Completeness:   {feas_payload['completeness_pct']}%")
    print(f"  Dominant break: {feas_payload['dominant_break']}")
    print(f"  Outputs in:     {args.out}")


if __name__ == "__main__":
    main()
