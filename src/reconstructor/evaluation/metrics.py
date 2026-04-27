"""Evaluation metrics: completeness, boundary F1, and seven-mode dominance."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..core.chain import DecisionChain
from ..mapping.operational_modes import OperationalMode, mode_to_break


def boundary_f1(
    detected_chain: DecisionChain,
    ground_truth_boundary_indices: list[int],
    total_fragments: int,
    tolerance: int = 1,
) -> float:
    """F1 of detected boundaries against ground-truth boundary indices.

    A detected boundary is a True Positive if a ground-truth boundary exists
    within +/- tolerance indices.
    """
    detected_indices: list[int] = []
    cumulative = 0
    for unit in detected_chain.units[:-1]:  # last unit has no closing boundary
        cumulative += len(unit.fragments)
        detected_indices.append(cumulative - 1)

    if not detected_indices and not ground_truth_boundary_indices:
        return 1.0
    if not detected_indices or not ground_truth_boundary_indices:
        return 0.0

    gt_set = set(ground_truth_boundary_indices)
    matched_gt: set[int] = set()
    tp = 0
    for d in detected_indices:
        hit = False
        for gt in gt_set:
            if gt in matched_gt:
                continue
            if abs(d - gt) <= tolerance:
                matched_gt.add(gt)
                tp += 1
                hit = True
                break
        _ = hit

    fp = len(detected_indices) - tp
    fn = len(ground_truth_boundary_indices) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class CellAggregate:
    """Aggregated metrics for a 3x2 matrix cell."""

    architecture: str
    stack_tier: str
    n_scenarios: int
    completeness_mean: float
    completeness_ci_low: float
    completeness_ci_high: float
    boundary_f1_mean: float
    modal_mode: OperationalMode | None
    modal_mode_share: float
    dominant_break: str | None


def bootstrap_ci(
    values: list[float], n_iter: int = 1000, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI."""
    if not values:
        return 0.0, 0.0
    rng = random.Random(42)
    means: list[float] = []
    n = len(values)
    for _ in range(n_iter):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_iter * alpha / 2)]
    hi = means[int(n_iter * (1 - alpha / 2))]
    return lo, hi


def aggregate_cell(
    architecture: str,
    stack_tier: str,
    completeness_scores: list[float],
    boundary_f1_scores: list[float],
    unrecoverable_modes_per_scenario: list[list[OperationalMode]],
) -> CellAggregate:
    """Aggregate per-scenario results into one cell summary."""
    n = len(completeness_scores)
    mean = sum(completeness_scores) / n if n else 0.0
    lo, hi = bootstrap_ci(completeness_scores)
    f1_mean = sum(boundary_f1_scores) / len(boundary_f1_scores) if boundary_f1_scores else 0.0

    mode_counts: dict[OperationalMode, int] = {}
    total_modes = 0
    for modes in unrecoverable_modes_per_scenario:
        for m in modes:
            mode_counts[m] = mode_counts.get(m, 0) + 1
            total_modes += 1
    if mode_counts:
        modal = max(mode_counts, key=lambda k: mode_counts[k])
        share = mode_counts[modal] / total_modes
        dominant = mode_to_break(modal).value
    else:
        modal = None
        share = 0.0
        dominant = None

    return CellAggregate(
        architecture=architecture,
        stack_tier=stack_tier,
        n_scenarios=n,
        completeness_mean=mean,
        completeness_ci_low=lo,
        completeness_ci_high=hi,
        boundary_f1_mean=f1_mean,
        modal_mode=modal,
        modal_mode_share=share,
        dominant_break=dominant,
    )


def pct(x: float) -> str:
    """Format a proportion as percentage with 1 decimal."""
    if math.isnan(x):
        return "n/a"
    return f"{x * 100:.1f}"
