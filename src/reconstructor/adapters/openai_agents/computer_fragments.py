"""Computer-use fragment builders for OpenAI Agents spans."""

from __future__ import annotations

import json
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import OpenAIAgentsIngestOptions
from .fragment_common import _content_field, _fragment, _fragment_id


def _computer_use_fragments(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> list[Fragment]:
    data = span["span_data"]
    timestamp = float(span["_ts"])
    magnitude = 0.0 if "screenshot" in json.dumps(data, sort_keys=True).lower() else 1.0
    return [
        _fragment(
            _fragment_id(trace["trace_id"], span["span_id"], "computer_tool"),
            FragmentKind.TOOL_CALL,
            timestamp=timestamp,
            stack_tier=StackTier.CROSS_STACK,
            actor_id=actor_id,
            parent_trace_id=trace["trace_id"],
            decision_id_hint=trace["trace_id"],
            payload={
                "tool_name": str(data.get("tool_name") or "computer_use"),
                "args": _content_field(data.get("input"), True),
                "output": _content_field(data.get("output"), True),
            },
        ),
        _fragment(
            _fragment_id(trace["trace_id"], span["span_id"], "computer_state"),
            FragmentKind.STATE_MUTATION,
            timestamp=timestamp + 0.0001,
            stack_tier=StackTier.CROSS_STACK,
            actor_id=actor_id,
            parent_trace_id=trace["trace_id"],
            decision_id_hint=trace["trace_id"],
            payload={"state_change_magnitude": magnitude, "event": "computer use action executed"},
        ),
    ]
