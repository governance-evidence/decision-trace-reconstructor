"""Shared CrewAI adapter types and low-level helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeAlias

from ...core.fragment import StackTier

_Event: TypeAlias = dict[str, Any]
_QueueKey: TypeAlias = tuple[str, str, str]
_LogKey: TypeAlias = tuple[str, str]
_EXTERNAL_MEMORY_TYPES = {"long_term", "entity", "external"}
_SKIPPED_EVENT_TYPES = {
    "crew_kickoff_completed",
    "agent_execution_completed",
    "task_completed",
}


@dataclass(frozen=True)
class CrewAIIngestOptions:
    architecture: str = "multi_agent"
    auto_architecture: bool = False
    stack_tier: StackTier = StackTier.WITHIN_STACK
    cross_stack_tools_pattern: str | None = None
    state_mutation_tool_pattern: str | None = None
    actor_override: str | None = None
    crew_name: str | None = None
    emit_config_snapshot: bool = True


def _crew_name(event: dict[str, Any]) -> str:
    payload = event["payload"]
    return str(payload.get("crew_name") or payload.get("crew") or "crew_default")


def _matches(value: Any, pattern: str | None) -> bool:
    return bool(pattern and value and re.search(pattern, str(value)))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "crew"


def _to_epoch_seconds(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    raise TypeError(f"Unsupported CrewAI timestamp: {type(value)!r}")
