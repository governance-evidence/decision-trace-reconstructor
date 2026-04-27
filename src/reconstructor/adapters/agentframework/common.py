"""Shared Agent Framework adapter types and helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeAlias

from ...core.fragment import StackTier

_Event: TypeAlias = dict[str, Any]
_AgentKey: TypeAlias = tuple[str, str]
_QueueKey: TypeAlias = tuple[str, str, str]
_MANAGER_SENDERS = {"system", "<group_chat_manager>", "manager"}


@dataclass(frozen=True)
class AgentFrameworkIngestOptions:
    architecture: str = "single_agent"
    auto_architecture: bool = False
    stack_tier: StackTier = StackTier.WITHIN_STACK
    cross_stack_tools_pattern: str | None = None
    state_mutation_tool_pattern: str | None = None
    actor_override: str | None = None
    runtime: str | None = None
    topic_filter: str | None = None


def _event_allowed(event: dict[str, Any], opts: AgentFrameworkIngestOptions) -> bool:
    if not opts.topic_filter:
        return True
    topic = event.get("topic") or event["payload"].get("topic")
    if topic is None:
        return True
    return re.search(opts.topic_filter, str(topic)) is not None


def _matches(value: Any, pattern: str | None) -> bool:
    return bool(pattern and value and re.search(pattern, str(value)))


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
    raise TypeError(f"Unsupported Agent Framework timestamp: {type(value)!r}")
