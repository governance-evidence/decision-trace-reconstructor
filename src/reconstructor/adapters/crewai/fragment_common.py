"""Shared helpers for CrewAI fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import CrewAIIngestOptions, _crew_name, _matches, _slug


def _fragment(
    event: dict[str, Any],
    kind: FragmentKind,
    *,
    suffix: str,
    actor_id: str,
    stack_tier: StackTier,
    payload: dict[str, Any],
    ts_offset: float = 0.0,
) -> Fragment:
    crew_name = _crew_name(event)
    return Fragment(
        fragment_id=f"crewai_{_slug(crew_name)}_{event['event_id']}_{suffix}",
        timestamp=float(event["timestamp"]) + ts_offset,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        payload=payload,
        parent_trace_id=crew_name,
        decision_id_hint=str(event["payload"].get("task_id") or crew_name),
    )


def _actor_id(
    event: dict[str, Any],
    fallback_actor: str | None,
    opts: CrewAIIngestOptions,
) -> str:
    if opts.actor_override:
        return opts.actor_override
    payload = event["payload"]
    for field in ("agent_role", "assigned_agent", "from_agent", "to_agent"):
        if payload.get(field):
            return str(payload[field])
    return fallback_actor or f"agent_{_slug(_crew_name(event))}"


def _tool_stack_tier(payload: dict[str, Any], opts: CrewAIIngestOptions) -> StackTier:
    if _matches(payload.get("tool_name"), opts.cross_stack_tools_pattern):
        return StackTier.CROSS_STACK
    return opts.stack_tier
