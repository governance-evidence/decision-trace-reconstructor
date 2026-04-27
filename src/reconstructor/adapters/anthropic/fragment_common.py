"""Shared Anthropic fragment helpers."""

from __future__ import annotations

import re
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import AnthropicIngestOptions


def _actor_id(
    request: dict[str, Any], response: dict[str, Any], opts: AnthropicIngestOptions
) -> str:
    if opts.actor_override:
        return opts.actor_override
    metadata = request.get("metadata") or {}
    if metadata.get("user_id"):
        return str(metadata["user_id"])
    system = request.get("system")
    if isinstance(system, str):
        first_line = system.strip().splitlines()[0] if system.strip() else ""
        match = re.match(r"You are\s+([^.,:]+)", first_line, re.IGNORECASE)
        if match:
            return match.group(1).strip().replace(" ", "_")
    if response.get("model"):
        return str(response["model"])
    return f"agent_{str(response.get('id') or 'anthropic')[:12]}"


def _fragment(
    fragment_id: str,
    kind: FragmentKind,
    *,
    timestamp: float,
    stack_tier: StackTier,
    actor_id: str,
    parent_trace_id: str | None,
    decision_id_hint: str | None,
    payload: dict[str, Any],
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=decision_id_hint,
        payload=payload,
    )
