"""CrewAI telemetry loading and event normalisation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import _to_epoch_seconds


def load_events_file(path: str | Path) -> list[dict[str, Any]]:
    """Load CrewAI telemetry events from JSON or JSONL."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_crewai_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        events.extend(_normalise_crewai_input(json.loads(line), start_index=len(events)))
    return events


def normalise_crewai_input(data: Any) -> list[dict[str, Any]]:
    """Normalise CrewAI telemetry payloads into event dicts."""
    return _normalise_crewai_input(data, start_index=0)


def _normalise_crewai_input(data: Any, *, start_index: int) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [_normalise_event(item, start_index + index) for index, item in enumerate(data)]
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported CrewAI payload: {type(data)!r}")
    if "events" in data and isinstance(data["events"], list):
        return [
            _normalise_event(item, start_index + index) for index, item in enumerate(data["events"])
        ]
    if data.get("event_type") or data.get("eventType"):
        return [_normalise_event(data, start_index)]
    raise ValueError(
        "Unsupported CrewAI payload: expected TelemetryEvent dict, list, or {events:[...]} wrapper"
    )


def _normalise_event(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported CrewAI event object: {type(data)!r}")
    payload = dict(data.get("payload") or {})
    for key, value in data.items():
        if key in {"payload", "timestamp", "ts", "event_type", "eventType", "event_id", "id"}:
            continue
        payload.setdefault(key, value)
    event_type = str(data.get("event_type") or data.get("eventType") or "unknown")
    return {
        "event_id": str(data.get("event_id") or data.get("id") or f"event_{index + 1:04d}"),
        "event_type": event_type,
        "timestamp": _to_epoch_seconds(data.get("timestamp") or data.get("ts")),
        "payload": payload,
        "_index": index,
    }
