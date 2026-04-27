"""Function-tool fragment builders for OpenAI Agents spans."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import OpenAIAgentsIngestOptions
from .fragment_common import (
    _content_field,
    _fragment,
    _fragment_id,
    _is_state_mutation,
    _stack_tier,
)


def _function_fragments(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> list[Fragment]:
    data = span["span_data"]
    tool_name = str(data.get("tool_name") or data.get("name") or "function")
    timestamp = float(span["_ts"])
    tier = _stack_tier(span, opts)
    out = [
        _fragment(
            _fragment_id(trace["trace_id"], span["span_id"], "tool"),
            FragmentKind.TOOL_CALL,
            timestamp=timestamp,
            stack_tier=tier,
            actor_id=actor_id,
            parent_trace_id=trace["trace_id"],
            decision_id_hint=trace["trace_id"],
            payload={
                "tool_name": tool_name,
                "args": _content_field(data.get("input"), True),
                "output": _content_field(data.get("output"), True),
            },
        )
    ]
    if _is_state_mutation(tool_name, opts):
        out.append(_state_mutation_fragment(span, trace, actor_id, tier, timestamp, tool_name))
    return out


def _state_mutation_fragment(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    tier: StackTier,
    timestamp: float,
    tool_name: str,
) -> Fragment:
    return _fragment(
        _fragment_id(trace["trace_id"], span["span_id"], "state"),
        FragmentKind.STATE_MUTATION,
        timestamp=timestamp + 0.0001,
        stack_tier=tier,
        actor_id=actor_id,
        parent_trace_id=trace["trace_id"],
        decision_id_hint=trace["trace_id"],
        payload={"state_change_magnitude": 1.0, "event": f"state mutation via {tool_name}"},
    )
