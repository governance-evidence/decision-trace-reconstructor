"""Fragment construction dispatch for OpenTelemetry GenAI spans."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from .common import OtlpIngestOptions, _get_attr, _span_override_kind
from .fragment_builders import (
    _agent_message_fragment,
    _config_fragment,
    _error_fragment,
    _message_event_fragments,
    _model_generation_fragment,
    _override_fragment,
    _tool_fragments,
)
from .fragment_common import _span_fragment_context


def _span_to_fragments(span: dict[str, Any], opts: OtlpIngestOptions) -> list[Fragment]:
    ctx = _span_fragment_context(span, opts)
    out: list[Fragment] = []

    override_kind = _span_override_kind(span)
    if override_kind is not None:
        out.append(_override_fragment(ctx, override_kind))
    elif ctx.operation in {"chat", "text_completion", "generate_content"}:
        out.append(_model_generation_fragment(ctx))
    elif ctx.operation == "execute_tool":
        out.extend(_tool_fragments(ctx))
    elif ctx.operation == "embeddings":
        return []
    elif ctx.operation == "create_agent":
        out.append(_config_fragment(ctx))
    elif ctx.operation == "invoke_agent" or _get_attr(span, "gen_ai.system"):
        out.append(_agent_message_fragment(ctx))

    out.extend(
        _message_event_fragments(
            span,
            opts.store_content,
            stack_tier=ctx.stack_tier,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
        )
    )

    if str((span.get("status") or {}).get("code", "OK")).upper() == "ERROR":
        out.append(_error_fragment(ctx))

    return out
