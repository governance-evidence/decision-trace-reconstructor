"""Bedrock terminal, retrieval, and policy trace fragment builders."""

from __future__ import annotations

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import _content_field, _fragment, _fragment_id, _is_human_approval
from .fragment_context import _BedrockEventContext


def _knowledge_base_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    return [
        _fragment(
            _fragment_id(ctx.session_id, "retrieval", ctx.timestamp),
            FragmentKind.RETRIEVAL_RESULT,
            timestamp=ctx.timestamp,
            stack_tier=ctx.stack_tier,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
            decision_id_hint=ctx.decision_id_hint,
            payload={
                "query": _content_field(
                    ctx.block.get("knowledgeBaseLookupInput") or {},
                    ctx.opts.store_content,
                ),
                "retrieved": _content_field(
                    ctx.block.get("knowledgeBaseLookupOutput") or {},
                    ctx.opts.store_content,
                ),
            },
        )
    ]


def _guardrail_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    return [
        _fragment(
            _fragment_id(ctx.session_id, "policy", ctx.timestamp),
            FragmentKind.POLICY_SNAPSHOT,
            timestamp=ctx.timestamp,
            stack_tier=ctx.stack_tier,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
            decision_id_hint=ctx.decision_id_hint,
            payload={
                "constraint_activated": True,
                "policy_id": ctx.block.get("guardrailId") or ctx.block.get("policyId"),
            },
        )
    ]


def _return_control_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    result = ctx.block.get("invocationResults")
    if not result:
        return []
    approved = _is_human_approval(result)
    return [
        _fragment(
            _fragment_id(ctx.session_id, "human", ctx.timestamp),
            FragmentKind.HUMAN_APPROVAL if approved else FragmentKind.HUMAN_REJECTION,
            timestamp=ctx.timestamp,
            stack_tier=StackTier.HUMAN,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
            decision_id_hint=ctx.decision_id_hint,
            payload={"result": _content_field(result, ctx.opts.store_content)},
        )
    ]


def _failure_fragments(ctx: _BedrockEventContext) -> list[Fragment]:
    return [
        _fragment(
            _fragment_id(ctx.session_id, "error", ctx.timestamp),
            FragmentKind.ERROR,
            timestamp=ctx.timestamp,
            stack_tier=ctx.stack_tier,
            actor_id=ctx.actor_id,
            parent_trace_id=ctx.parent_trace_id,
            decision_id_hint=ctx.decision_id_hint,
            payload={"error": ctx.block.get("failureReason") or ctx.block.get("message")},
        )
    ]
