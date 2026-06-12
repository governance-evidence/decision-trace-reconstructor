"""Shared OpenAI Agents adapter types and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...core.fragment import StackTier
from .._time import to_epoch_seconds


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
    return to_epoch_seconds(value, ms_heuristic=True)
