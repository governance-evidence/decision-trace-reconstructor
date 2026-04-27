"""Shared MCP adapter types and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ...core.fragment import StackTier

_SKIPPED_METHODS = {
    "initialized",
    "ping",
    "roots/list",
    "logging/setLevel",
    "notifications/cancelled",
    "notifications/progress",
    "notifications/message",
    "notifications/tools/list_changed",
}


@dataclass(frozen=True)
class McpIngestOptions:
    architecture: str = "single_agent"
    stack_tier: StackTier = StackTier.CROSS_STACK
    state_mutation_tool_pattern: str | None = None
    emit_tools_list: bool = False
    max_state_mutations_per_resource: int = 10
    store_uris: bool = False
    actor_override: str | None = None
    session_id: str | None = None


def _to_epoch_seconds(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0.0
        if stripped.isdigit():
            return float(stripped)
        return datetime.fromisoformat(stripped.replace("Z", "+00:00")).timestamp()
    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")
