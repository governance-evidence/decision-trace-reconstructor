"""Message, handoff, and guardrail fragment builders for OpenAI Agents spans."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import OpenAIAgentsIngestOptions
from .fragment_common import _content_field, _fragment, _fragment_id, _stack_tier


def _agent_message_fragment(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
    *,
    suffix: str,
) -> Fragment:
    data = span["span_data"]
    return _fragment(
        _fragment_id(trace["trace_id"], span["span_id"], suffix),
        FragmentKind.AGENT_MESSAGE,
        timestamp=float(span["_ts"]),
        stack_tier=_stack_tier(span, opts),
        actor_id=actor_id,
        parent_trace_id=trace["trace_id"],
        decision_id_hint=trace["trace_id"],
        payload={
            "content": _content_field(
                {"input": data.get("input"), "output": data.get("output")}, True
            ),
            "name": data.get("name"),
            "span_type": data.get("type"),
        },
    )


def _handoff_fragment(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> Fragment:
    data = span["span_data"]
    target = str(data.get("handoff_to") or data.get("handoffTo") or data.get("name") or actor_id)
    return _fragment(
        _fragment_id(trace["trace_id"], span["span_id"], "handoff"),
        FragmentKind.AGENT_MESSAGE,
        timestamp=float(span["_ts"]),
        stack_tier=_stack_tier(span, opts),
        actor_id=target,
        parent_trace_id=trace["trace_id"],
        decision_id_hint=trace["trace_id"],
        payload={"content": _content_field(data.get("input"), True), "handoff_to": target},
    )


def _guardrail_fragment(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> Fragment:
    data = span["span_data"]
    result = str(data.get("result") or "unknown").lower()
    return _fragment(
        _fragment_id(trace["trace_id"], span["span_id"], "guardrail"),
        FragmentKind.POLICY_SNAPSHOT,
        timestamp=float(span["_ts"]),
        stack_tier=_stack_tier(span, opts),
        actor_id=actor_id,
        parent_trace_id=trace["trace_id"],
        decision_id_hint=trace["trace_id"],
        payload={
            "constraint_activated": result == "passed",
            "result": result,
            "policy_id": data.get("name") or data.get("guardrail_name"),
        },
    )
