"""OTLP model generation fragment builders."""

from __future__ import annotations

from ...core.fragment import Fragment, FragmentKind
from .common import _get_attr
from .fragment_common import (
    _fragment,
    _fragment_id,
    _shape_payload,
    _SpanFragmentContext,
)
from .fragment_payloads import _assistant_messages, _extract_media_descriptors


def _model_generation_fragment(ctx: _SpanFragmentContext) -> Fragment:
    input_tokens = _get_attr(ctx.span, "gen_ai.usage.input_tokens") or 0
    output_tokens = _get_attr(ctx.span, "gen_ai.usage.output_tokens") or 0
    media = _extract_media_descriptors(ctx.span)
    extra_payload = {
        "model_id": _get_attr(ctx.span, "gen_ai.response.model", "gen_ai.request.model")
        or "undisclosed",
        "internal_reasoning": "opaque",
        "token_count": int(input_tokens) + int(output_tokens),
        "assistant_messages": _assistant_messages(ctx.span, ctx.opts),
    }
    if media:
        extra_payload["media"] = media
    return _fragment(
        _fragment_id(ctx.span_id, "model"),
        FragmentKind.MODEL_GENERATION,
        payload=_shape_payload(ctx.span, extra_payload),
        timestamp=ctx.timestamp,
        stack_tier=ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
    )
