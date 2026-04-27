"""Tool, LLM, and memory fragment builders for CrewAI events."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import _EXTERNAL_MEMORY_TYPES, CrewAIIngestOptions
from .fragment_common import _fragment, _tool_stack_tier


def _tool_fragment(
    start_event: dict[str, Any],
    finish_event: dict[str, Any] | None,
    actor_id: str,
    opts: CrewAIIngestOptions,
    *,
    error: Any,
) -> Fragment:
    start_payload = start_event["payload"]
    finish_payload = finish_event["payload"] if finish_event is not None else {}
    payload = {
        "tool_name": start_payload.get("tool_name") or finish_payload.get("tool_name"),
        "args": dict(start_payload.get("args") or {}),
    }
    if finish_event is not None:
        payload["result"] = finish_payload.get("output")
    if error is not None:
        payload["error"] = error
    if finish_event is None and error is None:
        payload["incomplete"] = True
    return _fragment(
        start_event,
        FragmentKind.TOOL_CALL,
        suffix="tool_call",
        actor_id=actor_id,
        stack_tier=_tool_stack_tier(start_payload, opts),
        payload=payload,
    )


def _tool_state_fragment(
    start_event: dict[str, Any], actor_id: str, opts: CrewAIIngestOptions
) -> Fragment:
    payload = start_event["payload"]
    return _fragment(
        start_event,
        FragmentKind.STATE_MUTATION,
        suffix="tool_state",
        actor_id=actor_id,
        stack_tier=_tool_stack_tier(payload, opts),
        payload={
            "tool_name": payload.get("tool_name"),
            "args": dict(payload.get("args") or {}),
        },
        ts_offset=0.0001,
    )


def _llm_fragment(
    start_event: dict[str, Any],
    finish_event: dict[str, Any] | None,
    actor_id: str,
    opts: CrewAIIngestOptions,
    pending_logs: list[str],
) -> Fragment:
    start_payload = start_event["payload"]
    finish_payload = finish_event["payload"] if finish_event is not None else {}
    payload = {
        "model_id": start_payload.get("model") or finish_payload.get("model"),
        "messages": start_payload.get("messages") or [],
        "internal_reasoning": "opaque",
    }
    if finish_event is not None:
        payload["output"] = finish_payload.get("output")
        if finish_payload.get("tokens") is not None:
            payload["token_count"] = finish_payload.get("tokens")
    else:
        payload["incomplete"] = True
    if pending_logs:
        payload["agent_visible_log"] = "\n".join(item[:500] for item in pending_logs if item)
    return _fragment(
        start_event,
        FragmentKind.MODEL_GENERATION,
        suffix="llm_call",
        actor_id=actor_id,
        stack_tier=opts.stack_tier,
        payload=payload,
    )


def _memory_fragment(
    start_event: dict[str, Any],
    finish_event: dict[str, Any] | None,
    actor_id: str,
    opts: CrewAIIngestOptions,
) -> Fragment:
    start_payload = start_event["payload"]
    finish_payload = finish_event["payload"] if finish_event is not None else {}
    memory_type = str(
        start_payload.get("memory_type") or finish_payload.get("memory_type") or "memory"
    )
    payload = {
        "query": start_payload.get("query"),
        "memory_type": memory_type,
        "retrieved": finish_payload.get("results") or [],
    }
    if finish_event is None:
        payload["incomplete"] = True
    return _fragment(
        start_event,
        FragmentKind.RETRIEVAL_RESULT,
        suffix="memory_query",
        actor_id=actor_id,
        stack_tier=StackTier.CROSS_STACK
        if memory_type in _EXTERNAL_MEMORY_TYPES
        else opts.stack_tier,
        payload=payload,
    )
