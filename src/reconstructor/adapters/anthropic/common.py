"""Shared Anthropic adapter types and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ...core.fragment import StackTier

_DEFAULT_BASH_READONLY_PATTERN = (
    r"^(ls|cat|head|tail|pwd|echo|grep|find|stat|whoami|id|date|env|hostname)\b"
)
_COMPUTER_MUTATION_ACTIONS = {
    "left_click",
    "right_click",
    "middle_click",
    "double_click",
    "triple_click",
    "type",
    "key",
    "keydown",
    "keyup",
}
_COMPUTER_READONLY_ACTIONS = {"screenshot", "mouse_move", "scroll", "wait"}
_TEXT_EDITOR_MUTATION_ACTIONS = {"create", "insert", "replace", "str_replace", "undo_edit"}


@dataclass(frozen=True)
class AnthropicIngestOptions:
    architecture: str = "single_agent"
    stack_tier: StackTier = StackTier.WITHIN_STACK
    cross_stack_tools_pattern: str | None = None
    state_mutation_tool_pattern: str | None = None
    actor_override: str | None = None
    store_thinking: bool = False
    bash_readonly_pattern: str = _DEFAULT_BASH_READONLY_PATTERN


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
