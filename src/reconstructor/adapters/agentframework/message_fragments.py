"""Message, model, snapshot, and error builders for Agent Framework events."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import AgentFrameworkIngestOptions
from .fragment_common import _base_stack_tier, _fragment


def _message_fragment(
    event: dict[str, Any],
    actor_id: str,
    opts: AgentFrameworkIngestOptions,
    *,
    suffix: str,
    payload: dict[str, Any],
) -> Fragment:
    return _fragment(
        event,
        FragmentKind.AGENT_MESSAGE,
        suffix=suffix,
        actor_id=actor_id,
        stack_tier=_base_stack_tier(event, opts),
        payload=payload,
    )


def _agent_fragment(
    start_event: dict[str, Any],
    finish_event: dict[str, Any] | None,
    actor_id: str,
    opts: AgentFrameworkIngestOptions,
) -> Fragment:
    start_payload = start_event["payload"]
    payload = {
        "agent_id": start_payload.get("agent_id"),
        "agent_name": start_payload.get("agent_name"),
        "input": start_payload.get("input"),
    }
    if finish_event is not None:
        payload["output"] = finish_event["payload"].get("output")
    else:
        payload["incomplete"] = True
    return _fragment(
        start_event,
        FragmentKind.AGENT_MESSAGE,
        suffix="agent_call",
        actor_id=actor_id,
        stack_tier=_base_stack_tier(start_event, opts),
        payload=payload,
    )


def _model_fragment(
    start_event: dict[str, Any],
    finish_event: dict[str, Any] | None,
    actor_id: str,
    opts: AgentFrameworkIngestOptions,
) -> Fragment:
    start_payload = start_event["payload"]
    payload = {
        "model_id": start_payload.get("model")
        or (finish_event["payload"].get("model") if finish_event else None),
        "messages": start_payload.get("messages") or [],
        "client_type": start_payload.get("client_type")
        or (start_payload.get("metadata") or {}).get("client_type"),
        "internal_reasoning": "opaque",
    }
    if finish_event is not None:
        payload["choices"] = finish_event["payload"].get("choices") or []
    else:
        payload["incomplete"] = True
    return _fragment(
        start_event,
        FragmentKind.MODEL_GENERATION,
        suffix="model_call",
        actor_id=actor_id,
        stack_tier=_base_stack_tier(start_event, opts),
        payload=payload,
    )


def _snapshot_fragment(
    event: dict[str, Any],
    actor_id: str,
    opts: AgentFrameworkIngestOptions,
    kind: FragmentKind,
) -> Fragment:
    payload = dict(event["payload"])
    return _fragment(
        event,
        kind,
        suffix=kind.value,
        actor_id=actor_id,
        stack_tier=_base_stack_tier(event, opts),
        payload=payload,
    )


def _error_fragment(
    event: dict[str, Any], actor_id: str, opts: AgentFrameworkIngestOptions
) -> Fragment:
    return _fragment(
        event,
        FragmentKind.ERROR,
        suffix="error",
        actor_id=actor_id,
        stack_tier=_base_stack_tier(event, opts),
        payload={"error": dict(event["payload"])},
    )
