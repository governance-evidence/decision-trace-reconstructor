"""Override and error fragment builders for OpenAI Agents spans."""

from __future__ import annotations

from ...core.fragment import Fragment, FragmentKind
from .fragment_common import (
    _fragment,
    _fragment_id,
    _OpenAISpanContext,
    _stack_tier,
)


def _override_fragment(ctx: _OpenAISpanContext, kind_override: FragmentKind) -> Fragment:
    return _fragment(
        _fragment_id(ctx.trace["trace_id"], ctx.span["span_id"], "override"),
        kind_override,
        timestamp=ctx.timestamp,
        stack_tier=ctx.opts.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
        decision_id_hint=ctx.decision_id_hint,
        payload={
            "span_type": ctx.span_type,
            "name": (ctx.span.get("span_data") or {}).get("name"),
        },
    )


def _span_error_fragment(ctx: _OpenAISpanContext) -> Fragment:
    return _fragment(
        _fragment_id(ctx.trace["trace_id"], ctx.span["span_id"], "error"),
        FragmentKind.ERROR,
        timestamp=ctx.timestamp + 0.0001,
        stack_tier=_stack_tier(ctx.span, ctx.opts),
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
        decision_id_hint=ctx.decision_id_hint,
        payload={"error": ctx.span["error"]},
    )
