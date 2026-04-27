"""Tool and state-mutation builders for Agent Framework events."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import AgentFrameworkIngestOptions
from .fragment_common import _fragment, _tool_stack_tier


def _tool_fragment(
    start_event: dict[str, Any],
    finish_event: dict[str, Any] | None,
    actor_id: str,
    opts: AgentFrameworkIngestOptions,
) -> Fragment:
    start_payload = start_event["payload"]
    payload = {
        "tool_name": start_payload.get("tool_name"),
        "args": dict(start_payload.get("args") or {}),
    }
    if finish_event is not None:
        payload["result"] = finish_event["payload"].get("result")
    else:
        payload["incomplete"] = True
    return _fragment(
        start_event,
        FragmentKind.TOOL_CALL,
        suffix="tool_call",
        actor_id=actor_id,
        stack_tier=_tool_stack_tier(start_event, opts),
        payload=payload,
    )


def _state_fragment(
    start_event: dict[str, Any], actor_id: str, opts: AgentFrameworkIngestOptions
) -> Fragment:
    payload = start_event["payload"]
    return _fragment(
        start_event,
        FragmentKind.STATE_MUTATION,
        suffix="tool_state",
        actor_id=actor_id,
        stack_tier=_tool_stack_tier(start_event, opts),
        payload={"tool_name": payload.get("tool_name"), "args": dict(payload.get("args") or {})},
        ts_offset=0.0001,
    )
