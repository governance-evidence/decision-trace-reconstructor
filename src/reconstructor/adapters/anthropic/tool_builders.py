"""Fragment builders for Anthropic tool-use blocks."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .fragment_common import _fragment
from .tool_rules import _state_change_magnitude


def _tool_call_fragment(
    round_payload: dict[str, Any],
    actor_id: str,
    block: dict[str, Any],
    tool_use_id: str,
    result_payload: dict[str, Any] | None,
    tool_timestamp: float,
    tier: StackTier,
    parent_trace_id: str,
) -> Fragment:
    tool_name = str(block.get("name") or "tool")
    payload: dict[str, Any] = {
        "tool_name": tool_name,
        "args": block.get("input"),
    }
    if result_payload is not None:
        payload["result"] = result_payload["result"]
    return _fragment(
        f"anthropic_{round_payload['round_id']}_{tool_use_id}_tool",
        FragmentKind.TOOL_CALL,
        timestamp=tool_timestamp,
        stack_tier=tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=parent_trace_id,
        payload=payload,
    )


def _tool_state_fragment(
    round_payload: dict[str, Any],
    actor_id: str,
    block: dict[str, Any],
    tool_name: str,
    tool_use_id: str,
    tool_timestamp: float,
    tier: StackTier,
    parent_trace_id: str,
) -> Fragment:
    return _fragment(
        f"anthropic_{round_payload['round_id']}_{tool_use_id}_state",
        FragmentKind.STATE_MUTATION,
        timestamp=tool_timestamp + 0.000001,
        stack_tier=tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=parent_trace_id,
        payload={
            "state_change_magnitude": _state_change_magnitude(tool_name, block.get("input")),
            "event": f"state mutation via {tool_name}",
        },
    )


def _tool_error_fragment(
    round_payload: dict[str, Any],
    actor_id: str,
    tool_use_id: str,
    result_payload: dict[str, Any],
    tool_timestamp: float,
    tier: StackTier,
    parent_trace_id: str,
) -> Fragment:
    return _fragment(
        f"anthropic_{round_payload['round_id']}_{tool_use_id}_error",
        FragmentKind.ERROR,
        timestamp=tool_timestamp + 0.000002,
        stack_tier=tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=parent_trace_id,
        payload={"error": result_payload["result"]},
    )
