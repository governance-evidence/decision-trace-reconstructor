"""Model-generation fragment builders for OpenAI Agents spans."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import OpenAIAgentsIngestOptions
from .fragment_common import (
    _content_field,
    _fragment,
    _fragment_id,
    _reasoning_summary,
    _stack_tier,
    _token_count,
)


def _model_generation_fragment(
    span: dict[str, Any],
    trace: dict[str, Any],
    actor_id: str,
    opts: OpenAIAgentsIngestOptions,
) -> Fragment:
    data = span["span_data"]
    reasoning = _reasoning_summary(data)
    payload: dict[str, Any] = {
        "model_id": data.get("model") or "openai_undisclosed",
        "internal_reasoning": "opaque",
        "input": _content_field(data.get("input"), True),
        "output": _content_field(data.get("output"), True),
    }
    token_count = _token_count(data)
    if token_count is not None:
        payload["token_count"] = token_count
    if reasoning is not None:
        payload["reasoning_summary_length"] = len(reasoning)
        if opts.store_reasoning:
            payload["reasoning_summary"] = reasoning
    return _fragment(
        _fragment_id(trace["trace_id"], span["span_id"], "model"),
        FragmentKind.MODEL_GENERATION,
        timestamp=float(span["_ts"]),
        stack_tier=_stack_tier(span, opts),
        actor_id=actor_id,
        parent_trace_id=trace["trace_id"],
        decision_id_hint=trace["trace_id"],
        payload=payload,
    )
