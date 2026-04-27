"""Shared OTLP fragment construction primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import (
    OtlpIngestOptions,
    _actor_id,
    _get_attr,
    _operation_name,
    _stack_tier_for,
)
from .normalize import to_unix_seconds as _to_unix_seconds


@dataclass(frozen=True)
class _SpanFragmentContext:
    span: dict[str, Any]
    opts: OtlpIngestOptions
    timestamp: float
    stack_tier: StackTier
    actor_id: str
    parent_trace_id: str | None
    operation: str
    tool_name: Any

    @property
    def span_id(self) -> str:
        return str(self.span["span_id"])


def _span_fragment_context(span: dict[str, Any], opts: OtlpIngestOptions) -> _SpanFragmentContext:
    return _SpanFragmentContext(
        span=span,
        opts=opts,
        timestamp=_to_unix_seconds(span["start_time_unix_nano"]),
        stack_tier=_stack_tier_for(span, opts),
        actor_id=_actor_id(span, opts),
        parent_trace_id=span.get("parent_span_id"),
        operation=_operation_name(span),
        tool_name=_get_attr(span, "gen_ai.tool.name"),
    )


def _fragment_id(span_id: str, suffix: str) -> str:
    short = span_id.replace("-", "")[:12] or "unknown"
    return f"otlp_{short}_{suffix}"


def _fragment(
    fragment_id: str,
    kind: FragmentKind,
    *,
    timestamp: float,
    stack_tier: StackTier,
    actor_id: str,
    payload: dict[str, Any],
    parent_trace_id: str | None,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        payload=payload,
        parent_trace_id=parent_trace_id,
    )


def _shape_payload(span: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "otel_span_name": span.get("name"),
        "gen_ai_system": _get_attr(span, "gen_ai.system"),
        "otel_scope_name": (span.get("scope") or {}).get("name"),
        "otel_scope_version": (span.get("scope") or {}).get("version"),
    }
    if extra:
        payload.update(extra)
    return payload
