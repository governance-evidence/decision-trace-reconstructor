"""Shared OpenAI Agents span-fragment helpers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import OpenAIAgentsIngestOptions


@dataclass(frozen=True)
class _OpenAISpanContext:
    span: dict[str, Any]
    trace: dict[str, Any]
    opts: OpenAIAgentsIngestOptions
    actor_id: str
    timestamp: float
    span_type: str
    parent_trace_id: str
    decision_id_hint: str


def _openai_span_context(
    span: dict[str, Any],
    trace: dict[str, Any],
    span_index: dict[str, dict[str, Any]],
    opts: OpenAIAgentsIngestOptions,
) -> _OpenAISpanContext:
    trace_id = trace["trace_id"]
    return _OpenAISpanContext(
        span=span,
        trace=trace,
        opts=opts,
        actor_id=_actor_id(span, trace, span_index, opts),
        timestamp=float(span["_ts"]),
        span_type=str((span.get("span_data") or {}).get("type") or "custom"),
        parent_trace_id=trace_id,
        decision_id_hint=trace_id,
    )


def _fragment(
    fragment_id: str,
    kind: FragmentKind,
    *,
    timestamp: float,
    stack_tier: StackTier,
    actor_id: str,
    parent_trace_id: str | None,
    decision_id_hint: str | None,
    payload: dict[str, Any],
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=decision_id_hint,
        payload=payload,
    )


def _fragment_id(trace_id: str, span_id: str, suffix: str) -> str:
    short = trace_id.replace("-", "")[:10] or "unknown"
    return f"openai_{short}_{span_id}_{suffix}"


def _stack_tier(span: dict[str, Any], opts: OpenAIAgentsIngestOptions) -> StackTier:
    span_type = str((span.get("span_data") or {}).get("type") or "custom")
    if span_type in {"web_search", "computer_use"}:
        return StackTier.CROSS_STACK
    if span_type == "function":
        tool_name = str(
            (span.get("span_data") or {}).get("tool_name")
            or (span.get("span_data") or {}).get("name")
            or ""
        )
        if tool_name in set(opts.cross_stack_tools):
            return StackTier.CROSS_STACK
    return opts.stack_tier


def _is_state_mutation(tool_name: str, opts: OpenAIAgentsIngestOptions) -> bool:
    if opts.state_mutation_tool_pattern and re.search(
        opts.state_mutation_tool_pattern, tool_name, re.IGNORECASE
    ):
        return True
    return False


def _override_kind(span: dict[str, Any]) -> FragmentKind | None:
    metadata = span.get("metadata") or {}
    span_meta = (span.get("span_data") or {}).get("metadata") or {}
    demm_kind = metadata.get("demm_kind") or span_meta.get("demm_kind")
    if demm_kind == "config_snapshot":
        return FragmentKind.CONFIG_SNAPSHOT
    return None


def _actor_id(
    span: dict[str, Any],
    trace: dict[str, Any],
    span_index: dict[str, dict[str, Any]],
    opts: OpenAIAgentsIngestOptions,
) -> str:
    if opts.actor_override:
        return opts.actor_override

    data = span.get("span_data") or {}
    span_type = str(data.get("type") or "")
    if span_type == "handoff" and (data.get("handoff_to") or data.get("handoffTo")):
        return str(data.get("handoff_to") or data.get("handoffTo"))
    if data.get("name"):
        return str(data["name"])

    parent_id = span.get("parent_id")
    visited: set[str] = set()
    while isinstance(parent_id, str) and parent_id not in visited:
        visited.add(parent_id)
        parent = span_index.get(parent_id)
        if parent is None:
            break
        pdata = parent.get("span_data") or {}
        if pdata.get("type") == "handoff" and (pdata.get("handoff_to") or pdata.get("handoffTo")):
            return str(pdata.get("handoff_to") or pdata.get("handoffTo"))
        if pdata.get("name"):
            return str(pdata["name"])
        parent_id = parent.get("parent_id")

    if trace.get("workflow_name"):
        return str(trace["workflow_name"])
    return f"agent_{str(trace['trace_id'])[:8]}"


def _content_field(content: Any, preserve_raw: bool) -> Any:
    if content is None:
        return None
    if preserve_raw:
        return content
    encoded = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {"sha256": digest, "length": len(encoded)}


def _reasoning_summary(span_data: dict[str, Any]) -> str | None:
    output = span_data.get("output")
    if isinstance(output, dict):
        reasoning = output.get("reasoning")
        if isinstance(reasoning, str):
            return reasoning
        if isinstance(reasoning, dict):
            summary = reasoning.get("summary") or reasoning.get("text")
            if isinstance(summary, str):
                return summary
    return None


def _token_count(span_data: dict[str, Any]) -> int | None:
    input_tokens = span_data.get("input_tokens")
    output_tokens = span_data.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    return None
