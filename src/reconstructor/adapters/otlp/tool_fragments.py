"""OTLP tool-call related fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import _is_state_mutating
from .fragment_common import (
    _fragment,
    _fragment_id,
    _shape_payload,
    _SpanFragmentContext,
)
from .fragment_payloads import (
    _retrieval_result_from_tool,
    _tool_args,
    _tool_result_payload,
)


def _tool_fragments(ctx: _SpanFragmentContext) -> list[Fragment]:
    out = [
        _fragment(
            _fragment_id(ctx.span_id, "tool"),
            FragmentKind.TOOL_CALL,
            payload=_shape_payload(
                ctx.span,
                {
                    "tool_name": ctx.tool_name or ctx.span.get("name"),
                    "args": _tool_args(ctx.span, ctx.opts),
                    "result": _tool_result_payload(ctx.span, ctx.opts),
                },
            ),
            timestamp=ctx.timestamp,
            stack_tier=ctx.stack_tier,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
        )
    ]
    if _is_state_mutating(str(ctx.tool_name or ""), ctx.opts):
        out.append(_tool_state_fragment(ctx))
    retrieval = _retrieval_result_from_tool(ctx.span, ctx.opts)
    if retrieval is not None:
        out.append(_tool_retrieval_fragment(ctx, retrieval))
    return out


def _tool_state_fragment(ctx: _SpanFragmentContext) -> Fragment:
    return _fragment(
        _fragment_id(ctx.span_id, "state"),
        FragmentKind.STATE_MUTATION,
        payload=_shape_payload(
            ctx.span,
            {
                "state_change_magnitude": 1.0,
                "event": f"state mutation via {ctx.tool_name or ctx.span.get('name')}",
            },
        ),
        timestamp=ctx.timestamp + 0.001,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )


def _tool_retrieval_fragment(ctx: _SpanFragmentContext, retrieval: dict[str, Any]) -> Fragment:
    return _fragment(
        _fragment_id(ctx.span_id, "retrieval"),
        FragmentKind.RETRIEVAL_RESULT,
        payload=_shape_payload(ctx.span, retrieval),
        timestamp=ctx.timestamp + 0.0015,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )
