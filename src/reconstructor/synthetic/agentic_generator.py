"""Agentic synthetic scenario generation."""

from __future__ import annotations

import random

from ..core.architecture import Architecture, coerce_architecture
from ..core.fragment import Fragment, FragmentKind, StackTier
from .scenario import Scenario


def generate_scenario(
    architecture: Architecture | str,
    stack_tier: StackTier,
    seed: int,
) -> Scenario:
    """Generate one scenario with deterministic seed."""
    arch = coerce_architecture(architecture)
    rng = random.Random(seed)  # noqa: S311 (prototype, not security-sensitive)
    chain_depth = rng.randint(5, 12)
    frags: list[Fragment] = []
    boundaries: list[int] = []

    t = 1_700_000_000.0 + seed * 100.0
    actor_ids = _actors_for(arch, rng)
    primary_actor = actor_ids[0]

    for step in range(chain_depth):
        actor = _pick_actor(arch, actor_ids, step, rng)
        kinds = _step_kinds(arch, stack_tier, step, chain_depth, rng)

        for kind in kinds:
            t += rng.uniform(0.1, 2.0)
            frag = _make_fragment(
                fid=f"s{seed}_f{len(frags):03d}",
                ts=t,
                kind=kind,
                actor=actor,
                stack_tier=stack_tier if kind != FragmentKind.HUMAN_APPROVAL else StackTier.HUMAN,
                step=step,
                primary_actor=primary_actor,
                rng=rng,
            )
            frags.append(frag)

        if step < chain_depth - 1:
            boundaries.append(len(frags) - 1)

    return Scenario(
        scenario_id=f"{arch.value}_{stack_tier.value}_seed{seed}",
        architecture=arch,
        stack_tier=stack_tier,
        seed=seed,
        fragments=frags,
        ground_truth_boundaries=boundaries,
    )


def _actors_for(architecture: Architecture, rng: random.Random) -> list[str]:
    if architecture is Architecture.SINGLE_AGENT:
        return [f"agent_{rng.randint(1000, 9999)}"]
    if architecture is Architecture.MULTI_AGENT:
        return [f"agent_{rng.randint(1000, 9999)}" for _ in range(rng.randint(3, 5))]
    if architecture is Architecture.HUMAN_IN_THE_LOOP:
        return [f"agent_{rng.randint(1000, 9999)}", f"operator_{rng.randint(100, 999)}"]
    return ["system"]


def _pick_actor(arch: Architecture, actors: list[str], step: int, rng: random.Random) -> str:
    if arch is Architecture.MULTI_AGENT:
        return rng.choice(actors)
    if arch is Architecture.HUMAN_IN_THE_LOOP and step % 3 == 2:
        return actors[-1]  # operator step
    return actors[0]


def _step_kinds(
    arch: Architecture,
    tier: StackTier,
    step: int,
    depth: int,
    rng: random.Random,
) -> list[FragmentKind]:
    """Return ordered fragment kinds for this step."""
    kinds: list[FragmentKind] = []
    if step == 0:
        kinds.append(FragmentKind.CONFIG_SNAPSHOT)
        kinds.append(FragmentKind.POLICY_SNAPSHOT)
    if arch is Architecture.MULTI_AGENT:
        kinds.append(FragmentKind.AGENT_MESSAGE)
    kinds.append(FragmentKind.MODEL_GENERATION)

    if tier == StackTier.WITHIN_STACK or rng.random() < 0.7:
        kinds.append(FragmentKind.TOOL_CALL)

    if tier == StackTier.WITHIN_STACK or rng.random() < 0.4:
        kinds.append(FragmentKind.RETRIEVAL_RESULT)

    if rng.random() < 0.3:
        kinds.append(FragmentKind.STATE_MUTATION)

    if arch is Architecture.HUMAN_IN_THE_LOOP and step % 3 == 2:
        kinds.append(
            FragmentKind.HUMAN_APPROVAL if rng.random() < 0.8 else FragmentKind.HUMAN_REJECTION
        )
    return kinds


def _make_fragment(
    *,
    fid: str,
    ts: float,
    kind: FragmentKind,
    actor: str,
    stack_tier: StackTier,
    step: int,
    primary_actor: str,
    rng: random.Random,
) -> Fragment:
    payload: dict[str, object] = {"step": step, "primary_actor": primary_actor}
    if kind == FragmentKind.STATE_MUTATION:
        payload["state_change_magnitude"] = rng.uniform(0.2, 1.0)
    if kind == FragmentKind.POLICY_SNAPSHOT:
        payload["constraint_activated"] = rng.random() < 0.3
        payload["policy_id"] = f"pol_{rng.randint(1, 20)}"
    if kind == FragmentKind.TOOL_CALL:
        payload["tool_name"] = rng.choice(["search", "write", "exec", "query", "fetch"])
        payload["args"] = {"key": rng.randint(0, 99)}
    if kind == FragmentKind.MODEL_GENERATION:
        payload["model_id"] = rng.choice(["gpt-4o", "claude-3-5", "llama-70b"])
        payload["token_count"] = rng.randint(50, 2000)
    return Fragment(
        fragment_id=fid,
        timestamp=ts,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor,
        payload=payload,
        parent_trace_id=None,
    )
