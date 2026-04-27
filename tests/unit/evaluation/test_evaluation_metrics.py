"""Unit tests for synthetic-evaluation metrics."""

from __future__ import annotations

import math

from reconstructor.core.chain import DecisionChain, DecisionUnit
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.evaluation.metrics import aggregate_cell, bootstrap_ci, boundary_f1, pct
from reconstructor.mapping.operational_modes import OperationalMode


def _fragment(index: int) -> Fragment:
    return Fragment(
        fragment_id=f"f{index}",
        timestamp=float(index),
        kind=FragmentKind.AGENT_MESSAGE,
        stack_tier=StackTier.WITHIN_STACK,
        actor_id="agent",
        payload={"index": index},
    )


def _chain_with_unit_lengths(lengths: list[int]) -> DecisionChain:
    fragments = [_fragment(index) for index in range(sum(lengths))]
    units: list[DecisionUnit] = []
    offset = 0
    for unit_index, length in enumerate(lengths):
        unit_fragments = fragments[offset : offset + length]
        units.append(
            DecisionUnit(
                unit_id=f"u{unit_index}",
                fragments=unit_fragments,
                boundary_reason="tool_call",
                boundary_confidence=0.8,
            )
        )
        offset += length
    return DecisionChain(chain_id="chain", units=units, source_fragments=fragments)


def test_boundary_f1_handles_empty_and_missing_boundaries() -> None:
    empty_chain = DecisionChain(chain_id="empty")
    assert boundary_f1(empty_chain, [], total_fragments=0) == 1.0
    assert boundary_f1(empty_chain, [1], total_fragments=3) == 0.0
    assert boundary_f1(_chain_with_unit_lengths([2, 2]), [], total_fragments=4) == 0.0


def test_boundary_f1_matches_with_tolerance_without_reusing_ground_truth() -> None:
    chain = _chain_with_unit_lengths([2, 3, 1])
    assert boundary_f1(chain, [1, 4], total_fragments=6, tolerance=0) == 1.0
    assert boundary_f1(chain, [2, 5], total_fragments=6, tolerance=1) == 1.0
    assert boundary_f1(chain, [1], total_fragments=6, tolerance=0) == 2 / 3


def test_bootstrap_ci_handles_empty_and_is_bounded() -> None:
    assert bootstrap_ci([]) == (0.0, 0.0)
    lo, hi = bootstrap_ci([0.2, 0.6, 1.0], n_iter=50)
    assert 0.2 <= lo <= hi <= 1.0


def test_aggregate_cell_handles_empty_inputs() -> None:
    aggregate = aggregate_cell(
        architecture="single_agent",
        stack_tier="within_stack",
        completeness_scores=[],
        boundary_f1_scores=[],
        unrecoverable_modes_per_scenario=[],
    )
    assert aggregate.n_scenarios == 0
    assert aggregate.completeness_mean == 0.0
    assert aggregate.boundary_f1_mean == 0.0
    assert aggregate.modal_mode is None
    assert aggregate.dominant_break is None


def test_aggregate_cell_counts_modal_mode_and_structural_break() -> None:
    aggregate = aggregate_cell(
        architecture="multi_agent",
        stack_tier="cross_stack",
        completeness_scores=[0.4, 0.8],
        boundary_f1_scores=[0.5, 1.0],
        unrecoverable_modes_per_scenario=[
            [OperationalMode.MODE_5_DELEGATION_CHAIN],
            [
                OperationalMode.MODE_5_DELEGATION_CHAIN,
                OperationalMode.MODE_3_CHANNEL_GAP,
            ],
        ],
    )
    assert aggregate.n_scenarios == 2
    assert math.isclose(aggregate.completeness_mean, 0.6)
    assert aggregate.boundary_f1_mean == 0.75
    assert aggregate.modal_mode is OperationalMode.MODE_5_DELEGATION_CHAIN
    assert aggregate.modal_mode_share == 2 / 3
    assert aggregate.dominant_break == "decision_diffusion"


def test_pct_formats_nan_and_percentages() -> None:
    assert pct(0.1234) == "12.3"
    assert pct(math.nan) == "n/a"
