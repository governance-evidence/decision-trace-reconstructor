"""CrewAI manifest architecture inference."""

from __future__ import annotations

from typing import Any

from .common import CrewAIIngestOptions


def _infer_architecture(events: list[dict[str, Any]], opts: CrewAIIngestOptions) -> str:
    if not opts.auto_architecture:
        return opts.architecture

    if any(_has_human_input(event) for event in events):
        return "human_in_the_loop"

    actors: set[str] = set()
    process_name: str | None = None
    for event in events:
        payload = event["payload"]
        event_type = event["event_type"]
        if event_type == "crew_kickoff_started":
            process_name = str(payload.get("process") or process_name or "")
            for agent in payload.get("agents") or []:
                if isinstance(agent, dict):
                    role = agent.get("role") or agent.get("agent_role") or agent.get("name")
                else:
                    role = agent
                if role:
                    actors.add(str(role))
        for field in ("agent_role", "assigned_agent", "from_agent", "to_agent"):
            if payload.get(field):
                actors.add(str(payload[field]))

    actors.discard("Manager")
    if len(actors) <= 1 and (process_name or "").lower() == "sequential":
        return "single_agent"
    return "multi_agent"


def _has_human_input(event: dict[str, Any]) -> bool:
    payload = event["payload"]
    if payload.get("human_input"):
        return True
    if event["event_type"] == "crew_kickoff_started":
        return any(
            bool(task.get("human_input"))
            for task in payload.get("tasks") or []
            if isinstance(task, dict)
        )
    return False
