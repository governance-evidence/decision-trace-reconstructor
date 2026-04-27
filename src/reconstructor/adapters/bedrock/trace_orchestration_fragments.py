"""Bedrock orchestration trace fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import (
    _content_field,
    _fragment,
    _fragment_id,
    _is_state_mutation,
    _orchestration_tool_invocation,
    _tool_stack_tier,
)
from .fragment_context import _BedrockEventContext
from .trace_llm_fragments import _model_generation_fragment


def _orchestration_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    out: list[Fragment] = []
    model_input = ctx.block.get("modelInvocationInput") or {}
    model_output = ctx.block.get("modelInvocationOutput") or {}
    if model_input or model_output:
        payload = {
            "input": _content_field(model_input, ctx.opts.store_content),
            "output": _content_field(model_output, ctx.opts.store_content),
        }
        rationale = ctx.block.get("rationale") or {}
        if rationale:
            payload["rationale"] = _content_field(rationale, ctx.opts.store_content)
        out.append(
            _model_generation_fragment(
                ctx.session,
                suffix="orch_llm",
                timestamp=ctx.timestamp,
                actor_id=ctx.actor_id,
                parent_trace_id=ctx.parent_trace_id,
                decision_id_hint=ctx.decision_id_hint,
                payload=payload,
                opts=ctx.opts,
            )
        )

    invocation_input = ctx.block.get("invocationInput") or {}
    tool_invocation = _orchestration_tool_invocation(
        invocation_input,
        ctx.opts.store_content,
    )
    if tool_invocation is not None:
        out.extend(_orchestration_tool_fragments(ctx, tool_invocation, len(out)))

    observation = ctx.block.get("observation") or {}
    if observation.get("finalResponse"):
        out.append(
            _fragment(
                _fragment_id(ctx.session_id, f"final_{len(out)}", ctx.timestamp + 0.003),
                FragmentKind.AGENT_MESSAGE,
                timestamp=ctx.timestamp + 0.003,
                stack_tier=ctx.stack_tier,
                actor_id=ctx.actor_id,
                parent_trace_id=ctx.parent_trace_id,
                decision_id_hint=ctx.decision_id_hint,
                payload={
                    "content": _content_field(
                        observation.get("finalResponse"),
                        ctx.opts.store_content,
                    ),
                    "phase": "final",
                },
            )
        )
    return out


def _orchestration_tool_fragments(
    ctx: _BedrockEventContext,
    tool_invocation: dict[str, Any],
    suffix_index: int,
) -> list[Fragment]:
    tool_name = str(tool_invocation["tool_name"])
    tool_stack_tier = _tool_stack_tier(tool_name, ctx.opts)
    tool_timestamp = ctx.timestamp + 0.001
    out = [
        _fragment(
            _fragment_id(ctx.session_id, f"tool_{suffix_index}", tool_timestamp),
            FragmentKind.TOOL_CALL,
            timestamp=tool_timestamp,
            stack_tier=tool_stack_tier,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
            decision_id_hint=ctx.decision_id_hint,
            payload={
                "tool_name": tool_name,
                "args": tool_invocation["args"],
                "verb": tool_invocation["verb"],
            },
        )
    ]
    if _is_state_mutation(
        tool_name,
        tool_invocation["verb"],
        ctx.opts,
        force=bool(tool_invocation.get("force_state_mutation", False)),
    ):
        out.append(
            _fragment(
                _fragment_id(ctx.session_id, f"state_{suffix_index + 1}", tool_timestamp + 0.001),
                FragmentKind.STATE_MUTATION,
                timestamp=tool_timestamp + 0.001,
                stack_tier=tool_stack_tier,
                actor_id=ctx.actor_id,
                parent_trace_id=ctx.parent_trace_id,
                decision_id_hint=ctx.decision_id_hint,
                payload={
                    "state_change_magnitude": 1.0,
                    "event": f"state mutation via {tool_name}",
                },
            )
        )
    return out
