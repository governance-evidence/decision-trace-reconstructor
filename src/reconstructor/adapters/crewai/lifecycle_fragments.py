"""Lifecycle, coordination, policy, and error fragment builders for CrewAI events."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import CrewAIIngestOptions, _crew_name
from .fragment_common import _fragment


def _config_fragment(event: dict[str, Any], actor_id: str, opts: CrewAIIngestOptions) -> Fragment:
    payload = event["payload"]
    return _fragment(
        event,
        FragmentKind.CONFIG_SNAPSHOT,
        suffix="crew_config",
        actor_id=actor_id,
        stack_tier=opts.stack_tier,
        payload={
            "crew_name": _crew_name(event),
            "agents": payload.get("agents") or [],
            "tasks": payload.get("tasks") or [],
            "process": payload.get("process"),
        },
    )


def _message_fragment(
    event: dict[str, Any],
    actor_id: str,
    opts: CrewAIIngestOptions,
    *,
    suffix: str,
    payload_extra: dict[str, Any],
) -> Fragment:
    return _fragment(
        event,
        FragmentKind.AGENT_MESSAGE,
        suffix=suffix,
        actor_id=actor_id,
        stack_tier=opts.stack_tier,
        payload=payload_extra,
    )


def _policy_fragment(event: dict[str, Any], actor_id: str, opts: CrewAIIngestOptions) -> Fragment:
    payload = dict(event["payload"])
    payload.setdefault("constraint_activated", True)
    return _fragment(
        event,
        FragmentKind.POLICY_SNAPSHOT,
        suffix="policy_snapshot",
        actor_id=actor_id,
        stack_tier=opts.stack_tier,
        payload=payload,
    )


def _error_fragment(
    event: dict[str, Any],
    actor_id: str,
    opts: CrewAIIngestOptions,
    error: Any,
    *,
    suffix: str,
) -> Fragment:
    return _fragment(
        event,
        FragmentKind.ERROR,
        suffix=suffix,
        actor_id=actor_id,
        stack_tier=opts.stack_tier,
        payload={"error": error},
    )
