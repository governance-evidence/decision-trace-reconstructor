"""OpenAI Agents span-type fragment dispatch."""

from __future__ import annotations

from ...core.fragment import Fragment
from .fragment_common import _OpenAISpanContext, _override_kind
from .message_fragments import (
    _agent_message_fragment,
    _guardrail_fragment,
    _handoff_fragment,
)
from .model_fragments import _model_generation_fragment
from .special_fragments import _override_fragment, _span_error_fragment
from .tool_fragments import (
    _computer_use_fragments,
    _file_search_fragment,
    _function_fragments,
    _web_search_fragments,
)


def _primary_span_fragments(ctx: _OpenAISpanContext) -> list[Fragment]:
    span = ctx.span
    trace = ctx.trace
    opts = ctx.opts
    kind_override = _override_kind(span)
    if kind_override is not None:
        return [_override_fragment(ctx, kind_override)]
    if ctx.span_type in {"response", "generation"}:
        return [_model_generation_fragment(span, trace, ctx.actor_id, opts)]
    if ctx.span_type == "function":
        return _function_fragments(span, trace, ctx.actor_id, opts)
    if ctx.span_type == "web_search":
        return _web_search_fragments(span, trace, ctx.actor_id, opts)
    if ctx.span_type == "file_search":
        return [_file_search_fragment(span, trace, ctx.actor_id, opts)]
    if ctx.span_type == "computer_use":
        return _computer_use_fragments(span, trace, ctx.actor_id, opts)
    if ctx.span_type == "agent":
        return [_agent_message_fragment(span, trace, ctx.actor_id, opts, suffix="agent")]
    if ctx.span_type == "handoff":
        return [_handoff_fragment(span, trace, ctx.actor_id, opts)]
    if ctx.span_type == "guardrail":
        return [_guardrail_fragment(span, trace, ctx.actor_id, opts)]
    return [_agent_message_fragment(span, trace, ctx.actor_id, opts, suffix="custom")]


__all__ = ["_primary_span_fragments", "_span_error_fragment"]
