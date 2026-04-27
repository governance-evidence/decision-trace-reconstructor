"""Shared Pydantic AI adapter types and helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ...core.fragment import StackTier


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
    raise TypeError(f"Unsupported Pydantic AI timestamp: {type(value)!r}")
