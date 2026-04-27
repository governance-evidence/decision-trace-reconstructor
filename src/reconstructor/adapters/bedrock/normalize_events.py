"""CloudWatch/direct Bedrock records to canonical event records."""

from __future__ import annotations

import json
from typing import Any

from .normalize_common import _TRACE_TYPES, _to_epoch_seconds


def _normalise_item_to_events(item: dict[str, Any]) -> list[dict[str, Any]]:
    if "message" in item:
        return _cloudwatch_event_to_events(item)
    if "sessionId" in item or "session_id" in item:
        return _direct_session_to_events(item)
    raise ValueError("Unsupported Bedrock record: expected CloudWatch event or direct session dump")


def _cloudwatch_event_to_events(item: dict[str, Any]) -> list[dict[str, Any]]:
    message = item.get("message")
    if isinstance(message, str):
        inner = json.loads(message)
    elif isinstance(message, dict):
        inner = dict(message)
    else:
        raise TypeError("CloudWatch event 'message' must be JSON string or dict")
    base_timestamp = _to_epoch_seconds(item.get("timestamp"))
    return _trace_payload_to_events(inner, base_timestamp)


def _direct_session_to_events(item: dict[str, Any]) -> list[dict[str, Any]]:
    base_timestamp = _to_epoch_seconds(
        item.get("timestamp") or item.get("eventTime") or item.get("startTime")
    )
    return _trace_payload_to_events(item, base_timestamp)


def _trace_payload_to_events(
    payload: dict[str, Any], base_timestamp: float
) -> list[dict[str, Any]]:
    session_id = str(payload.get("sessionId") or payload.get("session_id") or "session_unknown")
    trace = payload.get("trace") or {key: payload[key] for key in _TRACE_TYPES if key in payload}
    if not isinstance(trace, dict):
        raise TypeError("Bedrock trace payload must be a dict")

    events: list[dict[str, Any]] = []
    offset = 0.0
    for trace_type in _TRACE_TYPES:
        block = trace.get(trace_type)
        if not block:
            continue
        event_timestamp = (
            _to_epoch_seconds(_extract_block_timestamp(block)) or base_timestamp + offset
        )
        events.append(
            {
                "session_id": session_id,
                "agent_id": payload.get("agentId") or payload.get("agent_id"),
                "agent_alias_id": payload.get("agentAliasId") or payload.get("agent_alias_id"),
                "agent_version": payload.get("agentVersion") or payload.get("agent_version"),
                "foundation_model": payload.get("foundationModel")
                or payload.get("foundation_model"),
                "memory_id": payload.get("memoryId") or payload.get("memory_id"),
                "memory_contents": payload.get("memoryContents") or payload.get("memory_contents"),
                "memory_summary": payload.get("sessionSummary") or payload.get("memory_summary"),
                "trace_type": trace_type,
                "timestamp": event_timestamp,
                "block": block,
            }
        )
        offset += 0.001
    return events


def _extract_block_timestamp(block: dict[str, Any]) -> Any:
    for key in ("eventTime", "timestamp", "time", "createdAt"):
        if key in block:
            return block[key]
    for value in block.values():
        if isinstance(value, dict):
            for key in ("eventTime", "timestamp", "time", "createdAt"):
                if key in value:
                    return value[key]
    return None
