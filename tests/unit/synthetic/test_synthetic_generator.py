"""Tests for deterministic synthetic scenario generation."""

from __future__ import annotations

import random

from reconstructor.core.architecture import Architecture
from reconstructor.core.fragment import FragmentKind, StackTier
from reconstructor.synthetic.generator import (
    _append_baseline_fragment,
    _make_fragment,
    _non_agentic_baseline,
    _stable_seed,
    generate_matrix,
    generate_scenario,
)


def test_stable_seed_is_deterministic_and_input_sensitive() -> None:
    first = _stable_seed("single_agent", "within_stack", 0)
    assert first == _stable_seed("single_agent", "within_stack", 0)
    assert first != _stable_seed("single_agent", "cross_stack", 0)
    assert 0 <= first <= 0x7FFFFFFF


def test_generate_scenario_is_deterministic_for_same_seed() -> None:
    left = generate_scenario(Architecture.SINGLE_AGENT, StackTier.WITHIN_STACK, seed=7)
    right = generate_scenario("single_agent", StackTier.WITHIN_STACK, seed=7)
    assert left.scenario_id == right.scenario_id
    assert [fragment.to_dict() for fragment in left.fragments] == [
        fragment.to_dict() for fragment in right.fragments
    ]
    assert left.ground_truth_boundaries == right.ground_truth_boundaries


def test_generate_matrix_has_expected_cells_and_unique_ids() -> None:
    scenarios = generate_matrix(seeds_per_cell=1)
    assert len(scenarios) == 7
    assert len({scenario.scenario_id for scenario in scenarios}) == 7
    assert {scenario.architecture for scenario in scenarios} == {
        Architecture.SINGLE_AGENT,
        Architecture.MULTI_AGENT,
        Architecture.HUMAN_IN_THE_LOOP,
        Architecture.NON_AGENTIC,
    }


def test_human_in_the_loop_scenario_contains_human_fragment() -> None:
    scenario = generate_scenario(
        Architecture.HUMAN_IN_THE_LOOP,
        StackTier.WITHIN_STACK,
        seed=11,
    )
    assert any(fragment.stack_tier is StackTier.HUMAN for fragment in scenario.fragments)
    assert any(fragment.is_human_intervention() for fragment in scenario.fragments)


def test_non_agentic_baseline_shape_is_stable() -> None:
    scenario = _non_agentic_baseline(seed=13)
    assert scenario.architecture is Architecture.NON_AGENTIC
    assert scenario.stack_tier is StackTier.WITHIN_STACK
    assert scenario.ground_truth_boundaries == [3]
    assert [fragment.kind for fragment in scenario.fragments] == [
        FragmentKind.CONFIG_SNAPSHOT,
        FragmentKind.POLICY_SNAPSHOT,
        FragmentKind.RETRIEVAL_RESULT,
        FragmentKind.TOOL_CALL,
        FragmentKind.STATE_MUTATION,
        FragmentKind.HUMAN_APPROVAL,
        FragmentKind.MODEL_GENERATION,
        FragmentKind.AGENT_MESSAGE,
    ]


def test_make_fragment_populates_kind_specific_payloads() -> None:
    rng = random.Random(17)
    state = _make_fragment(
        fid="state",
        ts=1.0,
        kind=FragmentKind.STATE_MUTATION,
        actor="agent",
        stack_tier=StackTier.WITHIN_STACK,
        step=1,
        primary_actor="agent",
        rng=rng,
    )
    policy = _make_fragment(
        fid="policy",
        ts=2.0,
        kind=FragmentKind.POLICY_SNAPSHOT,
        actor="agent",
        stack_tier=StackTier.WITHIN_STACK,
        step=1,
        primary_actor="agent",
        rng=rng,
    )
    tool = _make_fragment(
        fid="tool",
        ts=3.0,
        kind=FragmentKind.TOOL_CALL,
        actor="agent",
        stack_tier=StackTier.WITHIN_STACK,
        step=1,
        primary_actor="agent",
        rng=rng,
    )
    model = _make_fragment(
        fid="model",
        ts=4.0,
        kind=FragmentKind.MODEL_GENERATION,
        actor="agent",
        stack_tier=StackTier.WITHIN_STACK,
        step=1,
        primary_actor="agent",
        rng=rng,
    )
    assert "state_change_magnitude" in state.payload
    assert "policy_id" in policy.payload
    assert "tool_name" in tool.payload
    assert "model_id" in model.payload


def test_append_baseline_fragment_increments_timestamp() -> None:
    fragments = []
    next_timestamp = _append_baseline_fragment(
        fragments,
        seed=3,
        index=0,
        timestamp=10.0,
        kind=FragmentKind.CONFIG_SNAPSHOT,
        actor_id="system",
        payload={"config": "v1"},
    )
    assert next_timestamp == 10.5
    assert fragments[0].fragment_id == "s3_f000"
    assert fragments[0].timestamp == 10.0
