"""LangSmith fragment builders."""

from __future__ import annotations

from ...core.fragment import Fragment, FragmentKind, StackTier
from .fragment_common import _new_fragment, _RunFragmentContext, _shape_payload
from .fragment_predicates import _is_human_node, _is_state_mutating_tool


def _policy_fragment(ctx: _RunFragmentContext) -> Fragment:
    return _new_fragment(
        ctx,
        "policy",
        FragmentKind.POLICY_SNAPSHOT,
        _shape_payload(
            ctx.run,
            {"constraint_activated": True, "policy_id": ctx.run.get("name")},
        ),
    )


def _config_fragment(ctx: _RunFragmentContext) -> Fragment:
    return _new_fragment(
        ctx,
        "config",
        FragmentKind.CONFIG_SNAPSHOT,
        _shape_payload(ctx.run, {"config_version": ctx.run.get("name")}),
    )


def _llm_fragment(ctx: _RunFragmentContext) -> Fragment:
    extra = ctx.run.get("extra") or {}
    meta = extra.get("metadata") if isinstance(extra, dict) else {}
    return _new_fragment(
        ctx,
        "llm",
        FragmentKind.MODEL_GENERATION,
        _shape_payload(
            ctx.run,
            {
                "model_id": (meta.get("ls_model_name") if isinstance(meta, dict) else None)
                or ctx.run.get("name")
                or "undisclosed",
                "internal_reasoning": "opaque",
                "token_count": (ctx.run.get("total_tokens") if "total_tokens" in ctx.run else None),
            },
        ),
    )


def _tool_fragments(ctx: _RunFragmentContext) -> list[Fragment]:
    tool_name = ctx.run.get("name") or "unknown_tool"
    out = [
        _new_fragment(
            ctx,
            "tool",
            FragmentKind.TOOL_CALL,
            _shape_payload(
                ctx.run,
                {
                    "tool_name": tool_name,
                    "args": ctx.run.get("inputs") or {},
                },
            ),
        )
    ]
    if _is_state_mutating_tool(tool_name, ctx.opts):
        out.append(
            _new_fragment(
                ctx,
                "state",
                FragmentKind.STATE_MUTATION,
                _shape_payload(
                    ctx.run,
                    {
                        "state_change_magnitude": 1.0,
                        "event": f"state mutation via {tool_name}",
                    },
                ),
                timestamp_offset=0.001,
            )
        )
    return out


def _retriever_fragment(ctx: _RunFragmentContext) -> Fragment:
    return _new_fragment(
        ctx,
        "retr",
        FragmentKind.RETRIEVAL_RESULT,
        _shape_payload(
            ctx.run,
            {
                "retrieved": ctx.run.get("outputs") or {},
                "query": ctx.run.get("inputs") or {},
            },
        ),
    )


def _chain_or_prompt_fragment(ctx: _RunFragmentContext) -> Fragment:
    if _is_human_node(ctx.run, ctx.opts):
        return _human_fragment(ctx)
    return _new_fragment(
        ctx,
        "msg",
        FragmentKind.AGENT_MESSAGE,
        _shape_payload(
            ctx.run,
            {
                "content": ctx.run.get("inputs") or ctx.run.get("outputs") or {},
            },
        ),
    )


def _human_fragment(ctx: _RunFragmentContext) -> Fragment:
    error = ctx.run.get("error")
    kind = FragmentKind.HUMAN_REJECTION if error else FragmentKind.HUMAN_APPROVAL
    return _new_fragment(
        ctx,
        "human",
        kind,
        _shape_payload(
            ctx.run,
            {"approved_by": ctx.actor_id, "error": error},
        ),
        stack_tier=StackTier.HUMAN,
    )


def _error_fragment(ctx: _RunFragmentContext) -> Fragment:
    return _new_fragment(
        ctx,
        "err",
        FragmentKind.ERROR,
        _shape_payload(ctx.run, {"error": ctx.run.get("error")}),
        timestamp_offset=0.002,
    )
