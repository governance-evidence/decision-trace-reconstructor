"""Bedrock LLM-phase trace fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import BedrockIngestOptions, _content_field, _fragment, _fragment_id
from .fragment_context import _BedrockEventContext


def _pre_processing_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    model_input = ctx.block.get("modelInvocationInput") or {}
    model_output = ctx.block.get("modelInvocationOutput") or {}
    out: list[Fragment] = []

    if model_input:
        out.append(
            _fragment(
                _fragment_id(ctx.session_id, "pre_msg", ctx.timestamp),
                FragmentKind.AGENT_MESSAGE,
                timestamp=ctx.timestamp,
                stack_tier=ctx.stack_tier,
                actor_id=ctx.actor_id,
                parent_trace_id=ctx.parent_trace_id,
                decision_id_hint=ctx.decision_id_hint,
                payload={
                    "content": _content_field(model_input, ctx.opts.store_content),
                    "phase": "pre",
                },
            )
        )
    if model_output:
        out.append(
            _model_generation_fragment(
                ctx.session,
                suffix="pre_llm",
                timestamp=ctx.timestamp + 0.001,
                actor_id=ctx.actor_id,
                parent_trace_id=ctx.parent_trace_id,
                decision_id_hint=ctx.decision_id_hint,
                payload={
                    "output": _content_field(model_output, ctx.opts.store_content),
                    "phase": "pre",
                },
                opts=ctx.opts,
            )
        )
    return out


def _post_processing_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    return [
        _model_generation_fragment(
            ctx.session,
            suffix="post_llm",
            timestamp=ctx.timestamp,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
            decision_id_hint=ctx.decision_id_hint,
            payload={
                "input": _content_field(
                    ctx.block.get("modelInvocationInput") or {},
                    ctx.opts.store_content,
                ),
                "output": _content_field(
                    ctx.block.get("modelInvocationOutput") or {},
                    ctx.opts.store_content,
                ),
                "phase": "post",
            },
            opts=ctx.opts,
        )
    ]


def _model_generation_fragment(
    session: dict[str, Any],
    *,
    suffix: str,
    timestamp: float,
    actor_id: str,
    parent_trace_id: str | None,
    decision_id_hint: str,
    payload: dict[str, Any],
    opts: BedrockIngestOptions,
) -> Fragment:
    return _fragment(
        _fragment_id(session["session_id"], suffix, timestamp),
        FragmentKind.MODEL_GENERATION,
        timestamp=timestamp,
        stack_tier=opts.stack_tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=decision_id_hint,
        payload={
            "model_id": session.get("foundation_model") or "bedrock_undisclosed",
            "internal_reasoning": "opaque",
            **payload,
        },
    )
