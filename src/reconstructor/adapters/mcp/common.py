"""Shared MCP adapter types and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.fragment import StackTier
from .._time import to_epoch_seconds

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
    return to_epoch_seconds(value)
