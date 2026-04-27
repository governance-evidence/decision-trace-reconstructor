"""OTLP control, message, and error fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import _content_field, _get_attr
from .fragment_common import (
    _fragment,
    _fragment_id,
    _shape_payload,
    _SpanFragmentContext,
)
from .normalize import to_unix_seconds as _to_unix_seconds


def _override_fragment(ctx: _SpanFragmentContext, override_kind: FragmentKind) -> Fragment:
    return _fragment(
        _fragment_id(ctx.span_id, override_kind.value),
        override_kind,
        payload=_shape_payload(ctx.span, {"override": True}),
        timestamp=ctx.timestamp,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )


def _config_fragment(ctx: _SpanFragmentContext) -> Fragment:
    return _fragment(
        _fragment_id(ctx.span_id, "config"),
        FragmentKind.CONFIG_SNAPSHOT,
        payload=_shape_payload(
            ctx.span,
            {
                "config_version": _get_attr(ctx.span, "gen_ai.agent.id", "gen_ai.agent.name")
                or ctx.span.get("name"),
            },
        ),
        timestamp=ctx.timestamp,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )


def _agent_message_fragment(ctx: _SpanFragmentContext) -> Fragment:
    return _fragment(
        _fragment_id(ctx.span_id, "msg"),
        FragmentKind.AGENT_MESSAGE,
        payload=_shape_payload(ctx.span, {"content": ctx.span.get("name")}),
        timestamp=ctx.timestamp,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )


def _error_fragment(ctx: _SpanFragmentContext) -> Fragment:
    return _fragment(
        _fragment_id(ctx.span_id, "error"),
        FragmentKind.ERROR,
        payload=_shape_payload(ctx.span, {"error": (ctx.span.get("status") or {}).get("message")}),
        timestamp=ctx.timestamp + 0.002,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )


def _message_event_fragments(
    span: dict[str, Any],
    opts_store_content: bool,
    *,
    stack_tier: StackTier,
    actor_id: str,
    parent_trace_id: str | None,
) -> list[Fragment]:
    out: list[Fragment] = []
    for index, event in enumerate(span.get("events", [])):
        event_name = str(event.get("name") or "")
        if event_name not in {"gen_ai.user.message", "gen_ai.system.message"}:
            continue
        payload = _shape_payload(
            span,
            {
                "event_name": event_name,
                "role": event.get("attributes", {}).get("role"),
                "content": _content_field(
                    event.get("attributes", {}).get("content"), opts_store_content
                ),
            },
        )
        out.append(
            _fragment(
                _fragment_id(span["span_id"], f"event_{index}"),
                FragmentKind.AGENT_MESSAGE,
                payload=payload,
                timestamp=_to_unix_seconds(event["time_unix_nano"]),
                stack_tier=stack_tier,
                actor_id=actor_id,
                parent_trace_id=parent_trace_id,
            )
        )
    return out
