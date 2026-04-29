"""Artifact builders and writers for the synthetic evaluation."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ..mapping.feasibility import FeasibilityCategory
from ..output.prov_jsonld import cells_to_jsonld, per_scenario_summary_to_jsonld
from .metrics import aggregate_cell
from .synthetic_evaluation import _SyntheticEvaluation


@dataclass(frozen=True)
class _SyntheticOutputs:
    cells: list[dict[str, Any]]
    per_property_summary: dict[str, dict[str, float]]
    per_scenario_rows: list[dict[str, Any]]


def _build_outputs(evaluation: _SyntheticEvaluation) -> _SyntheticOutputs:
    return _SyntheticOutputs(
        cells=_cell_rows(evaluation),
        per_property_summary=_per_property_summary(evaluation.per_property_counts),
        per_scenario_rows=evaluation.per_scenario_rows,
    )


def _cell_rows(evaluation: _SyntheticEvaluation) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for (arch, tier), comp_scores in evaluation.per_cell_completeness.items():
        agg = aggregate_cell(
            architecture=arch,
            stack_tier=tier,
            completeness_scores=comp_scores,
            boundary_f1_scores=evaluation.per_cell_f1[(arch, tier)],
            unrecoverable_modes_per_scenario=evaluation.per_cell_modes[(arch, tier)],
        )
        cells.append(
            {
                "architecture": agg.architecture,
                "stack_tier": agg.stack_tier,
                "n": agg.n_scenarios,
                "completeness_pct": round(agg.completeness_mean * 100, 1),
                "completeness_ci_low": round(agg.completeness_ci_low * 100, 1),
                "completeness_ci_high": round(agg.completeness_ci_high * 100, 1),
                "boundary_f1": round(agg.boundary_f1_mean, 3),
                "modal_mode": agg.modal_mode.value if agg.modal_mode else None,
                "modal_mode_share": round(agg.modal_mode_share, 3),
                "dominant_break": agg.dominant_break,
            }
        )
    return cells


def _per_property_summary(
    per_property_counts: defaultdict[str, defaultdict[str, int]],
) -> dict[str, dict[str, float]]:
    per_property_summary: dict[str, dict[str, float]] = {}
    for prop, counts in per_property_counts.items():
        total = sum(counts.values())
        per_property_summary[prop] = {
            cat: round(v / total * 100, 1) if total else 0.0 for cat, v in counts.items()
        }
        for cat in FeasibilityCategory:
            per_property_summary[prop].setdefault(cat.value, 0.0)
    return per_property_summary


def _write_outputs(out_dir: Path, outputs: _SyntheticOutputs) -> None:
    (out_dir / "per_scenario.json").write_text(json.dumps(outputs.per_scenario_rows, indent=2))
    (out_dir / "per_scenario.jsonld").write_text(
        json.dumps(per_scenario_summary_to_jsonld(outputs.per_scenario_rows), indent=2)
    )
    _maybe_write_parquet(out_dir / "per_scenario.parquet", outputs.per_scenario_rows)
    (out_dir / "cells.json").write_text(json.dumps(outputs.cells, indent=2))
    (out_dir / "cells.jsonld").write_text(json.dumps(cells_to_jsonld(outputs.cells), indent=2))
    (out_dir / "per_property.json").write_text(json.dumps(outputs.per_property_summary, indent=2))


def _maybe_write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write ``rows`` as a Parquet sibling if ``pyarrow`` is available.

    Parquet is an optional dependency (``pip install -e '.[parquet]'``).
    When it is missing we silently skip, leaving the canonical JSON intact.
    """
    if not rows:
        return
    try:
        import pyarrow as pa  # type: ignore[import-not-found,unused-ignore]
        import pyarrow.parquet as pq  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return
    from_pylist = cast(Callable[[list[dict[str, Any]]], Any], pa.Table.from_pylist)
    write_table = cast(Callable[..., None], pq.write_table)
    table = from_pylist(rows)
    write_table(table, path, compression="snappy")
