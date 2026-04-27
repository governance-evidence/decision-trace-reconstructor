"""OpenAI Agents span-to-fragment conversion entrypoint."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from .common import OpenAIAgentsIngestOptions
from .fragment_builders import _primary_span_fragments, _span_error_fragment
from .fragment_common import _openai_span_context


def _span_to_fragments(
    span: dict[str, Any],
    trace: dict[str, Any],
    span_index: dict[str, dict[str, Any]],
    opts: OpenAIAgentsIngestOptions,
) -> list[Fragment]:
    ctx = _openai_span_context(span, trace, span_index, opts)
    out = _primary_span_fragments(ctx)
    if span.get("error"):
        out.append(_span_error_fragment(ctx))
    return out
