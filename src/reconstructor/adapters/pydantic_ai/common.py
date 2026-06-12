"""Shared Pydantic AI adapter types and helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ...core.fragment import StackTier
from .._time import to_epoch_seconds_lenient


@dataclass(frozen=True)
class PydanticAIIngestOptions:
    architecture: str = "single_agent"
    auto_architecture: bool = False
    stack_tier: StackTier = StackTier.WITHIN_STACK
    cross_stack_tools_pattern: str | None = None
    state_mutation_tool_pattern: str | None = None
    takeover_tool_pattern: str | None = None
    human_approval_pattern: str | None = None
    emit_system_prompt: bool = False
    actor_override: str | None = None


def _matches(value: Any, pattern: str | None) -> bool:
    return bool(pattern and value and re.search(pattern, str(value)))


def _to_epoch_seconds(value: Any) -> float:
    return to_epoch_seconds_lenient(value, label="Pydantic AI")
