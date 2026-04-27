"""Shared Pydantic AI fragment helpers."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import PydanticAIIngestOptions


def _actor_id(run_payload: dict[str, Any], opts: PydanticAIIngestOptions) -> str:
    if opts.actor_override:
        return opts.actor_override
    if run_payload.get("agent_name"):
        return str(run_payload["agent_name"])
    return f"agent_{str(run_payload['model']).replace(':', '_')}"


def _fragment(
    run_payload: dict[str, Any],
    *,
    fragment_id: str,
    timestamp: float,
    kind: FragmentKind,
    stack_tier: StackTier,
    actor_id: str,
    payload: dict[str, Any],
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=float(timestamp),
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        payload=payload,
        parent_trace_id=run_payload["run_id"],
        decision_id_hint=run_payload["run_id"],
    )
