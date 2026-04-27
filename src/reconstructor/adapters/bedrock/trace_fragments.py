"""Bedrock trace-event fragment dispatch."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from .common import BedrockIngestOptions
from .fragment_context import _event_context
from .trace_llm_fragments import _post_processing_fragments, _pre_processing_fragments
from .trace_orchestration_fragments import _orchestration_fragments
from .trace_terminal_fragments import (
    _failure_fragments,
    _guardrail_fragments,
    _knowledge_base_fragments,
    _return_control_fragments,
)


def _event_to_fragments(
    event: dict[str, Any],
    session: dict[str, Any],
    opts: BedrockIngestOptions,
) -> list[Fragment]:
    ctx = _event_context(event, session, opts)

    if ctx.trace_type == "preProcessingTrace":
        return _pre_processing_fragments(ctx)
    if ctx.trace_type == "orchestrationTrace":
        return _orchestration_fragments(ctx)
    if ctx.trace_type == "knowledgeBaseLookupTrace":
        return _knowledge_base_fragments(ctx)
    if ctx.trace_type == "postProcessingTrace":
        return _post_processing_fragments(ctx)
    if ctx.trace_type == "guardrailTrace":
        return _guardrail_fragments(ctx)
    if ctx.trace_type == "returnControl":
        return _return_control_fragments(ctx)
    if ctx.trace_type == "failureTrace":
        return _failure_fragments(ctx)
    return []
