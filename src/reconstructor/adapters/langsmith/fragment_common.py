"""Shared LangSmith fragment context and primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import LangSmithIngestOptions


@dataclass(frozen=True)
class _RunFragmentContext:
    run: dict[str, Any]
    opts: LangSmithIngestOptions
    run_type: str
    run_id: str
    timestamp: float
    actor_id: str
    stack_tier: StackTier
    parent_trace_id: Any


def _run_fragment_context(run: dict[str, Any], opts: LangSmithIngestOptions) -> _RunFragmentContext:
    return _RunFragmentContext(
        run=run,
        opts=opts,
        run_type=(run.get("run_type") or "").lower(),
        run_id=str(run.get("id")),
        timestamp=float(run["_ts"]),
        actor_id=_actor_id(run, opts),
        stack_tier=_stack_tier_for(run, opts),
        parent_trace_id=run.get("parent_run_id"),
    )


def _actor_id(run: dict[str, Any], opts: LangSmithIngestOptions) -> str:
    if opts.actor_override:
        return opts.actor_override
    extra = run.get("extra") or {}
    metadata = extra.get("metadata") if isinstance(extra, dict) else None
    if isinstance(metadata, dict):
        for key in ("langgraph_node", "agent_name", "actor_id"):
            value = metadata.get(key)
            if value:
                return str(value)
    name = run.get("name")
    if name:
        return str(name)
    rid = run.get("id", "")
    return f"agent_{str(rid)[:8]}"


def _stack_tier_for(run: dict[str, Any], opts: LangSmithIngestOptions) -> StackTier:
    """Per-fragment stack tier defaults to the manifest tier; some runs
    (browser-tool calls, MCP-mediated steps) may opt into ``cross_stack``
    via tag ``cross_stack``.
    """
    tags = run.get("tags") or []
    if "cross_stack" in tags:
        return StackTier.CROSS_STACK
    return opts.stack_tier


def _frag_id(run_id: str, suffix: str = "") -> str:
    short = run_id.replace("-", "")[:12]
    return f"ls_{short}{('_' + suffix) if suffix else ''}"


def _shape_payload(run: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Standard payload skeleton for any LangSmith-derived fragment."""
    payload: dict[str, Any] = {
        "langsmith_run_type": run.get("run_type"),
        "langsmith_run_name": run.get("name"),
    }
    if extra:
        payload.update(extra)
    return payload


def _new_fragment(
    ctx: _RunFragmentContext,
    suffix: str,
    kind: FragmentKind,
    payload: dict[str, Any],
    *,
    timestamp_offset: float = 0.0,
    stack_tier: StackTier | None = None,
) -> Fragment:
    return Fragment(
        fragment_id=_frag_id(ctx.run_id, suffix),
        timestamp=ctx.timestamp + timestamp_offset,
        kind=kind,
        stack_tier=stack_tier or ctx.stack_tier,
        actor_id=ctx.actor_id,
        parent_trace_id=ctx.parent_trace_id,
        payload=payload,
    )
