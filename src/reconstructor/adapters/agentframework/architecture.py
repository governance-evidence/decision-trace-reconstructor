"""Agent Framework manifest architecture inference."""

from __future__ import annotations

from typing import Any

from .common import AgentFrameworkIngestOptions


def _infer_architecture(events: list[dict[str, Any]], opts: AgentFrameworkIngestOptions) -> str:
    if not opts.auto_architecture:
        return opts.architecture
    if any(_is_human_proxy(event) for event in events):
        return "human_in_the_loop"
    if any(event["event_type"] == "speaker_selected" for event in events):
        return "multi_agent"
    agent_ids = {
        str(event["payload"].get("agent_id") or event["payload"].get("agent_name"))
        for event in events
        if event["event_type"] == "agent_called"
        and (event["payload"].get("agent_id") or event["payload"].get("agent_name"))
    }
    return "multi_agent" if len(agent_ids) >= 2 else "single_agent"


def _is_human_proxy(event: dict[str, Any]) -> bool:
    payload = event["payload"]
    if payload.get("is_human_proxy"):
        return True
    for field in ("agent_name", "agent_id"):
        value = str(payload.get(field) or "")
        if value and ("human" in value.lower() or "proxy" in value.lower()):
            return True
    sender = str(event.get("sender") or "")
    return bool(sender and ("human" in sender.lower() or "proxy" in sender.lower()))
