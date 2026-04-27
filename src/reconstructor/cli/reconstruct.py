"""CLI implementation for the ``reconstruct`` command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..core.manifest import FragmentManifest
from ..mapping.feasibility import FeasibilityCategory, PropertyFeasibility
from ..mapping.mapper import map_chain_to_schema_aggregate
from ..output.prov_jsonld import chain_to_jsonld
from ..pipeline import ReconstructionReport, reconstruct
from ..synthetic.generator import Scenario


class _ManifestError(ValueError):
    """User-facing manifest validation error."""


def _cmd_reconstruct(args: argparse.Namespace) -> int:
    data = json.loads(args.input.read_text())
    try:
        manifest = _parse_manifest(data)
    except _ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = reconstruct(
        fragments=manifest.fragments,
        architecture=manifest.architecture,
        stack_tier=manifest.stack_tier,
        chain_id=manifest.scenario_id,
    )
    chain_feas = map_chain_to_schema_aggregate(
        report.chain,
        manifest.architecture,
        manifest.stack_tier,
    )

    args.out.mkdir(parents=True, exist_ok=True)
    feas_payload = _feasibility_payload(manifest, report, chain_feas)
    _write_reconstruct_outputs(
        args.out,
        bool(args.jsonld),
        manifest,
        report,
        chain_feas,
        feas_payload,
    )
    _print_reconstruct_summary(args.out, manifest, report, feas_payload)
    return 0


def add_reconstruct_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_reconstruct = sub.add_parser(
        "reconstruct",
        help="Run the six-stage pipeline against a fragment manifest.",
    )
    p_reconstruct.add_argument("input", type=Path, help="Path to fragments JSON manifest.")
    p_reconstruct.add_argument(
        "--out",
        type=Path,
        default=Path("out"),
        help="Output directory (default: ./out).",
    )
    p_reconstruct.add_argument(
        "--jsonld",
        action="store_true",
        help="Also emit a PROV-O JSON-LD trace alongside feasibility.json.",
    )
    p_reconstruct.set_defaults(func=_cmd_reconstruct)


def _parse_manifest(data: dict[str, Any]) -> FragmentManifest:
    try:
        return FragmentManifest.from_dict(data)
    except KeyError as exc:
        if exc.args and str(exc.args[0]).startswith("FragmentManifest.from_dict:"):
            message = str(exc.args[0]).replace("FragmentManifest.from_dict: ", "input manifest ")
            raise _ManifestError(message) from exc
        raise _ManifestError(str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise _ManifestError(str(exc)) from exc


def _feasibility_payload(
    manifest: FragmentManifest,
    report: ReconstructionReport,
    chain_feas: list[PropertyFeasibility],
) -> dict[str, Any]:
    dominant_mode = report.dominant_mode()
    dominant_break = report.dominant_break()
    return {
        "scenario_id": manifest.scenario_id,
        "architecture": manifest.architecture.value,
        "stack_tier": manifest.stack_tier.value,
        "fragments": len(manifest.fragments),
        "units_detected": len(report.chain.units),
        "completeness_pct": round(report.completeness * 100, 1),
        "dominant_mode": dominant_mode.value if dominant_mode is not None else None,
        "dominant_break": dominant_break.value if dominant_break is not None else None,
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


def _write_reconstruct_outputs(
    out_dir: Path,
    emit_jsonld: bool,
    manifest: FragmentManifest,
    report: ReconstructionReport,
    chain_feas: list[PropertyFeasibility],
    feas_payload: dict[str, Any],
) -> None:
    (out_dir / "feasibility.json").write_text(json.dumps(feas_payload, indent=2) + "\n")

    if not emit_jsonld:
        return
    scenario = Scenario(
        scenario_id=manifest.scenario_id,
        architecture=manifest.architecture,
        stack_tier=manifest.stack_tier,
        seed=-1,
        fragments=manifest.fragments,
        ground_truth_boundaries=[],
    )
    (out_dir / "trace.jsonld").write_text(
        json.dumps(chain_to_jsonld(scenario, report, chain_feas), indent=2) + "\n"
    )


def _print_reconstruct_summary(
    out_dir: Path,
    manifest: FragmentManifest,
    report: ReconstructionReport,
    feas_payload: dict[str, Any],
) -> None:
    print(f"reconstructed {manifest.scenario_id}")
    print(f"  fragments in:   {len(manifest.fragments)}")
    print(f"  units detected: {len(report.chain.units)}")
    print(f"  completeness:   {feas_payload['completeness_pct']}%")
    print(f"  dominant break: {feas_payload['dominant_break']}")
    print(f"  outputs:        {out_dir}")
