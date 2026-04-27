"""Reconstruct named incidents and emit per-property feasibility table.

Outputs (raw JSON is canonical wire format; siblings are governance-grade):
- ``named_incidents.json``   -- flat summary array (validated by Pydantic models)
- ``named_incidents.jsonld`` -- W3C PROV-O bundle with full Activity/Entity/Agent graph
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..mapping.feasibility import FeasibilityCategory, PropertyFeasibility
from ..mapping.mapper import map_chain_to_schema_aggregate
from ..output.prov_jsonld import chains_to_jsonld_bundle
from ..pipeline import ReconstructionReport, reconstruct
from ..synthetic.generator import Scenario
from ..synthetic.named_incidents import all_named_incidents
from .defaults import DEFAULT_EVALUATION_OUT_DIR

_BundleItem = tuple[Scenario, ReconstructionReport, list[PropertyFeasibility]]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_EVALUATION_OUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    rows, bundle_items = _evaluate_named_incidents()
    _write_outputs(args.out, rows, bundle_items)
    _print_summary_table(rows)
    return 0


def _evaluate_named_incidents() -> tuple[list[dict[str, Any]], list[_BundleItem]]:
    rows: list[dict[str, Any]] = []
    bundle_items: list[_BundleItem] = []
    for sc in all_named_incidents():
        report, agg = _reconstruct_incident(sc)
        rows.append(_incident_row(sc, report, agg))
        bundle_items.append((sc, report, agg))
    return rows, bundle_items


def _reconstruct_incident(
    sc: Scenario,
) -> tuple[ReconstructionReport, list[PropertyFeasibility]]:
    report = reconstruct(
        fragments=sc.fragments,
        architecture=sc.architecture,
        stack_tier=sc.stack_tier,
        chain_id=sc.scenario_id,
    )
    agg = map_chain_to_schema_aggregate(report.chain, sc.architecture, sc.stack_tier)
    return report, agg


def _incident_row(
    sc: Scenario,
    report: ReconstructionReport,
    agg: list[PropertyFeasibility],
) -> dict[str, Any]:
    dominant_mode = report.dominant_mode()
    dominant_break = report.dominant_break()
    return {
        "incident": sc.scenario_id,
        "architecture": sc.architecture.value,
        "stack_tier": sc.stack_tier.value,
        "fragments": len(sc.fragments),
        "units_detected": len(report.chain.units),
        "completeness_pct": round(report.completeness * 100, 1),
        "dominant_mode": dominant_mode.value if dominant_mode is not None else None,
        "dominant_break": dominant_break.value if dominant_break is not None else None,
        "feasibility_counts": _feasibility_counts(agg),
        "per_property": [
            {
                "property": f.property_name,
                "category": f.category.value,
                "gap": f.gap_description,
            }
            for f in agg
        ],
    }


def _feasibility_counts(agg: list[PropertyFeasibility]) -> dict[str, int]:
    counts = {cat.value: 0 for cat in FeasibilityCategory}
    for feas in agg:
        counts[feas.category.value] += 1
    return counts


def _write_outputs(
    out_dir: Path, rows: list[dict[str, Any]], bundle_items: list[_BundleItem]
) -> None:
    (out_dir / "named_incidents.json").write_text(json.dumps(rows, indent=2))
    (out_dir / "named_incidents.jsonld").write_text(
        json.dumps(chains_to_jsonld_bundle(bundle_items), indent=2)
    )


def _print_summary_table(rows: list[dict[str, Any]]) -> None:
    print("Table 7. Named-incident reconstruction feasibility summary")
    header = (
        f"{'incident':<42} | {'arch':<12} | {'tier':<12} | "
        f"{'full':<5} | {'part':<5} | {'struct':<7} | {'opaque':<6} | compl%"
    )
    print(header)
    for r in rows:
        c = r["feasibility_counts"]
        print(
            f"{r['incident']:<42} | {r['architecture']:<12} | {r['stack_tier']:<12} | "
            f"{c['fully_fillable']:<5} | {c['partially_fillable']:<5} | "
            f"{c['structurally_unfillable']:<7} | {c['opaque']:<6} | "
            f"{r['completeness_pct']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
