"""Non-agentic synthetic baseline scenario generation."""

from __future__ import annotations

import random

from ..core.architecture import Architecture
from ..core.fragment import Fragment, FragmentKind, StackTier
from .scenario import Scenario

_BaselineFragmentSpec = tuple[FragmentKind, StackTier, str, dict[str, object]]


def _non_agentic_baseline(seed: int) -> Scenario:
    """Generate a non-agentic discrete-decision baseline scenario."""
    rng = random.Random(seed)  # noqa: S311
    t = 1_700_000_000.0 + seed * 100.0
    actor = f"rule_engine_{rng.randint(1, 9)}"
    frags: list[Fragment] = []

    for index, (kind, stack_tier, actor_id, payload) in enumerate(
        _baseline_fragment_specs(rng, actor)
    ):
        t = _append_baseline_fragment(
            frags,
            seed,
            index=index,
            timestamp=t,
            kind=kind,
            actor_id=actor_id,
            payload=payload,
            stack_tier=stack_tier,
        )
    return Scenario(
        scenario_id=f"non_agentic_baseline_seed{seed}",
        architecture=Architecture.NON_AGENTIC,
        stack_tier=StackTier.WITHIN_STACK,
        seed=seed,
        fragments=frags,
        ground_truth_boundaries=[3],  # single discrete decision
    )


def _baseline_fragment_specs(rng: random.Random, actor: str) -> list[_BaselineFragmentSpec]:
    specs: list[_BaselineFragmentSpec] = [
        (
            FragmentKind.CONFIG_SNAPSHOT,
            StackTier.WITHIN_STACK,
            actor,
            {"config_version": f"v{rng.randint(1, 30)}"},
        ),
        (
            FragmentKind.POLICY_SNAPSHOT,
            StackTier.WITHIN_STACK,
            actor,
            {"policy_id": f"pol_{rng.randint(1, 20)}", "constraint_activated": True},
        ),
        (
            FragmentKind.RETRIEVAL_RESULT,
            StackTier.WITHIN_STACK,
            actor,
            {"row_id": rng.randint(1000, 9999)},
        ),
        (
            FragmentKind.TOOL_CALL,
            StackTier.WITHIN_STACK,
            actor,
            {"tool_name": "decision_engine", "args": {}},
        ),
        (
            FragmentKind.STATE_MUTATION,
            StackTier.WITHIN_STACK,
            actor,
            {"state_change_magnitude": 1.0, "decision": "approve"},
        ),
    ]
    human_actor = f"operator_{rng.randint(100, 999)}"
    specs.extend(
        [
            (
                FragmentKind.HUMAN_APPROVAL,
                StackTier.HUMAN,
                human_actor,
                {"approved_by": f"operator_{rng.randint(100, 999)}"},
            ),
            (
                FragmentKind.MODEL_GENERATION,
                StackTier.WITHIN_STACK,
                actor,
                {"model_id": "rule_engine", "deterministic": True},
            ),
            (
                FragmentKind.AGENT_MESSAGE,
                StackTier.WITHIN_STACK,
                actor,
                {"content": "input received"},
            ),
        ]
    )
    return specs


def _append_baseline_fragment(
    frags: list[Fragment],
    seed: int,
    *,
    index: int,
    timestamp: float,
    kind: FragmentKind,
    actor_id: str,
    payload: dict[str, object],
    stack_tier: StackTier = StackTier.WITHIN_STACK,
) -> float:
    frags.append(
        Fragment(
            fragment_id=f"s{seed}_f{index:03d}",
            timestamp=timestamp,
            kind=kind,
            stack_tier=stack_tier,
            actor_id=actor_id,
            payload=payload,
        )
    )
    return timestamp + 0.5
