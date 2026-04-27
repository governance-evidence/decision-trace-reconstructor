"""Canonical Bedrock session normalization and completeness signals."""

from __future__ import annotations

from typing import Any

from .normalize_common import _SESSION_METADATA_KEYS
from .normalize_events import _normalise_item_to_events


def normalise_bedrock_input(data: Any) -> list[dict[str, Any]]:
    """Normalize CloudWatch / direct Bedrock payloads into canonical sessions."""
    items = _payload_items(data)

    sessions: dict[str, dict[str, Any]] = {}
    for item in items:
        for event in _normalise_item_to_events(item):
            session_id = event["session_id"]
            session = sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    **{key: event.get(key) for key in _SESSION_METADATA_KEYS},
                    "events": [],
                    "_ts": event["timestamp"],
                },
            )
            for key in _SESSION_METADATA_KEYS:
                if session.get(key) in (None, "") and event.get(key) not in (None, ""):
                    session[key] = event.get(key)
            session["events"].append(event)
            session["_ts"] = min(float(session["_ts"]), float(event["timestamp"]))

    out = list(sessions.values())
    for session in out:
        session["events"].sort(key=lambda event: (event["timestamp"], event["trace_type"]))
    out.sort(key=lambda session: (session["_ts"], session["session_id"]))
    return out


def normalise_session(session: dict[str, Any] | Any) -> dict[str, Any]:
    """Normalize one canonical or direct Bedrock session object."""
    if not isinstance(session, dict):
        raise TypeError(f"Unsupported Bedrock session object: {type(session)!r}")
    if "events" in session and isinstance(session["events"], list):
        events = [dict(event) for event in session["events"]]
        return {
            "session_id": str(
                session.get("session_id") or session.get("sessionId") or "session_unknown"
            ),
            "agent_id": session.get("agent_id") or session.get("agentId"),
            "agent_alias_id": session.get("agent_alias_id") or session.get("agentAliasId"),
            "agent_version": session.get("agent_version") or session.get("agentVersion"),
            "foundation_model": session.get("foundation_model") or session.get("foundationModel"),
            "memory_id": session.get("memory_id") or session.get("memoryId"),
            "memory_contents": session.get("memory_contents") or session.get("memoryContents"),
            "memory_summary": session.get("memory_summary") or session.get("sessionSummary"),
            "events": sorted(events, key=lambda event: (event["timestamp"], event["trace_type"])),
            "_ts": float(session.get("_ts") or (events[0]["timestamp"] if events else 0.0)),
        }
    direct_sessions = normalise_bedrock_input(session)
    if len(direct_sessions) != 1:
        raise ValueError("Direct Bedrock session normalization should produce exactly one session")
    return direct_sessions[0]


def has_terminal_signal(session: dict[str, Any]) -> bool:
    """Return whether a normalized session has a completion signal."""
    if session.get("memory_summary"):
        return True
    for event in session.get("events", []):
        trace_type = event.get("trace_type")
        block = event.get("block") or {}
        if trace_type in {"postProcessingTrace", "returnControl", "failureTrace"}:
            return True
        if trace_type == "orchestrationTrace":
            observation = block.get("observation") or {}
            if observation.get("finalResponse"):
                return True
    return False


def _payload_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [dict(item) for item in data]
    if isinstance(data, dict):
        if "events" in data and isinstance(data["events"], list):
            return [dict(item) for item in data["events"]]
        return [dict(data)]
    raise TypeError(f"Unsupported Bedrock payload type: {type(data)!r}")
