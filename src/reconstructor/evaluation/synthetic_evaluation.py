"""Evaluation loop for synthetic reconstruction scenarios."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..mapping.mapper import map_chain_to_schema_aggregate
from ..mapping.operational_modes import OperationalMode
from ..pipeline import ReconstructionReport, reconstruct
from ..synthetic.generator import Scenario
from .metrics import boundary_f1


def _float_lists() -> defaultdict[tuple[str, str], list[float]]:
    return defaultdict(list)


def _mode_lists() -> defaultdict[tuple[str, str], list[list[OperationalMode]]]:
    return defaultdict(list)


def _count_maps() -> defaultdict[str, defaultdict[str, int]]:
    return defaultdict(lambda: defaultdict(int))


@dataclass
class _SyntheticEvaluation:
    per_cell_completeness: defaultdict[tuple[str, str], list[float]] = field(
        default_factory=_float_lists
    )
    per_cell_f1: defaultdict[tuple[str, str], list[float]] = field(default_factory=_float_lists)
    per_cell_modes: defaultdict[tuple[str, str], list[list[OperationalMode]]] = field(
        default_factory=_mode_lists
    )
    per_property_counts: defaultdict[str, defaultdict[str, int]] = field(
        default_factory=_count_maps
    )
    per_scenario_rows: list[dict[str, Any]] = field(default_factory=list)

    def record(self, sc: Scenario) -> None:
        report = reconstruct(
            fragments=sc.fragments,
            architecture=sc.architecture,
            stack_tier=sc.stack_tier,
            chain_id=sc.scenario_id,
        )
        f1 = boundary_f1(
            detected_chain=report.chain,
            ground_truth_boundary_indices=sc.ground_truth_boundaries,
            total_fragments=len(sc.fragments),
            tolerance=1,
        )

        cell_key = (sc.architecture.value, sc.stack_tier.value)
        self.per_cell_completeness[cell_key].append(report.completeness)
        self.per_cell_f1[cell_key].append(f1)
        self.per_cell_modes[cell_key].append(list(report.unrecoverable_modes))

        agg_feas = map_chain_to_schema_aggregate(report.chain, sc.architecture, sc.stack_tier)
        for feas in agg_feas:
            self.per_property_counts[feas.property_name][feas.category.value] += 1

        self.per_scenario_rows.append(_scenario_row(sc, report, f1))


def _evaluate_scenarios(scenarios: list[Scenario]) -> _SyntheticEvaluation:
    evaluation = _SyntheticEvaluation()
    for sc in scenarios:
        evaluation.record(sc)
    return evaluation


def _scenario_row(sc: Scenario, report: ReconstructionReport, f1: float) -> dict[str, Any]:
    dominant_mode = report.dominant_mode()
    dominant_break = report.dominant_break()
    return {
        "scenario_id": sc.scenario_id,
        "architecture": sc.architecture.value,
        "stack_tier": sc.stack_tier.value,
        "seed": sc.seed,
        "fragments": len(sc.fragments),
        "units_detected": len(report.chain.units),
        "completeness": report.completeness,
        "boundary_f1": f1,
        "unrecoverable_mode_count": len(report.unrecoverable_modes),
        "dominant_mode": dominant_mode.value if dominant_mode is not None else None,
        "dominant_break": dominant_break.value if dominant_break is not None else None,
    }
