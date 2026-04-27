"""Shared OpenAI Agents adapter types and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...core.fragment import StackTier


@dataclass(frozen=True)
class OpenAIAgentsIngestOptions:
    architecture: str = "single_agent"
    stack_tier: StackTier = StackTier.WITHIN_STACK
    cross_stack_tools: tuple[str, ...] = field(default_factory=tuple)
    state_mutation_tool_pattern: str | None = None
    actor_override: str | None = None
    store_reasoning: bool = False
    auto_architecture: bool = False


def _to_epoch_seconds(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            return numeric / 1000.0
        return numeric
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0.0
        if stripped.isdigit():
            numeric = float(stripped)
            if numeric > 10_000_000_000:
                return numeric / 1000.0
            return numeric
        return datetime.fromisoformat(stripped.replace("Z", "+00:00")).timestamp()
    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")
