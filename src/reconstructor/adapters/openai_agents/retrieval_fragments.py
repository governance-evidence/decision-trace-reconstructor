"""Retrieval fragment builders for OpenAI Agents spans."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import OpenAIAgentsIngestOptions
from .fragment_common import _content_field, _fragment, _fragment_id, _stack_tier


def _web_search_fragments(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> list[Fragment]:
    data = span["span_data"]
    timestamp = float(span["_ts"])
    return [
        _fragment(
            _fragment_id(trace["trace_id"], span["span_id"], "web_tool"),
            FragmentKind.TOOL_CALL,
            timestamp=timestamp,
            stack_tier=StackTier.CROSS_STACK,
            actor_id=actor_id,
            parent_trace_id=trace["trace_id"],
            decision_id_hint=trace["trace_id"],
            payload={
                "tool_name": str(data.get("tool_name") or "web_search"),
                "args": _content_field(data.get("input"), True),
            },
        ),
        _fragment(
            _fragment_id(trace["trace_id"], span["span_id"], "web_retrieval"),
            FragmentKind.RETRIEVAL_RESULT,
            timestamp=timestamp + 0.0001,
            stack_tier=StackTier.CROSS_STACK,
            actor_id=actor_id,
            parent_trace_id=trace["trace_id"],
            decision_id_hint=trace["trace_id"],
            payload={
                "query": _content_field(data.get("input"), True),
                "retrieved": _content_field(data.get("output"), True),
            },
        ),
    ]


def _file_search_fragment(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> Fragment:
    data = span["span_data"]
    return _fragment(
        _fragment_id(trace["trace_id"], span["span_id"], "file_search"),
        FragmentKind.RETRIEVAL_RESULT,
        timestamp=float(span["_ts"]),
        stack_tier=_stack_tier(span, opts),
        actor_id=actor_id,
        parent_trace_id=trace["trace_id"],
        decision_id_hint=trace["trace_id"],
        payload={
            "query": _content_field(data.get("input"), True),
            "retrieved": _content_field(data.get("output"), True),
        },
    )
