"""Agent Framework event loading and normalisation."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from .common import _to_epoch_seconds


def load_events_file(path: str | Path) -> list[dict[str, Any]]:
    """Load Agent Framework events from JSON or JSONL."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_agentframework_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        events.extend(normalise_agentframework_input(json.loads(line)))
    return events


def normalise_agentframework_input(data: Any) -> list[dict[str, Any]]:
    """Normalize supported Agent Framework payloads."""
    if isinstance(data, list):
        return [_normalise_event(item, index) for index, item in enumerate(data)]
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Agent Framework payload: {type(data)!r}")
    if "events" in data and isinstance(data["events"], list):
        return [_normalise_event(item, index) for index, item in enumerate(data["events"])]
    if data.get("event_type") or data.get("eventType"):
        return [_normalise_event(data, 0)]
    raise ValueError(
        "Unsupported Agent Framework payload: expected event dict, list, or {events:[...]} wrapper"
    )


def _normalise_event(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Agent Framework event object: {type(data)!r}")

    payload = dict(data.get("payload") or {})
    event_type = _legacy_value(data, "event_type", ("eventType",), default="unknown")
    message_id = _legacy_value(
        data, "message_id", ("messageId", "id"), default=f"event_{index + 1:04d}"
    )
    trace_id = _legacy_value(data, "trace_id", ("traceId",), default="trace_unknown")
    topic = _legacy_value(data, "topic", (), default=None)
    sender = _legacy_value(data, "sender", (), default=None)
    recipient = _legacy_value(data, "recipient", (), default=None)

    for old_key, new_key in (
        ("agentName", "agent_name"),
        ("agentId", "agent_id"),
        ("toolName", "tool_name"),
        ("errorType", "error_type"),
        ("stackTrace", "stack_trace"),
        ("isHumanProxy", "is_human_proxy"),
    ):
        if old_key in payload and new_key not in payload:
            _warn_legacy(old_key, new_key)
            payload[new_key] = payload[old_key]

    return {
        "event_type": str(event_type),
        "message_id": str(message_id),
        "trace_id": str(trace_id),
        "topic": topic,
        "sender": sender,
        "recipient": recipient,
        "payload": payload,
        "timestamp": _to_epoch_seconds(
            data.get("ts") if data.get("ts") is not None else data.get("timestamp")
        ),
        "_index": index,
    }


def _legacy_value(
    data: dict[str, Any], key: str, legacy_keys: tuple[str, ...], *, default: Any
) -> Any:
    if key in data:
        return data[key]
    for legacy_key in legacy_keys:
        if legacy_key in data:
            _warn_legacy(legacy_key, key)
            return data[legacy_key]
    return default


def _warn_legacy(old_key: str, new_key: str) -> None:
    warnings.warn(
        f"legacy Agent Framework field {old_key!r} is deprecated; prefer {new_key!r}",
        DeprecationWarning,
        stacklevel=3,
    )
