"""Anthropic tool stack-tier and state-mutation rules."""

from __future__ import annotations

import re
from typing import Any

from ...core.fragment import StackTier
from .common import (
    _COMPUTER_MUTATION_ACTIONS,
    _TEXT_EDITOR_MUTATION_ACTIONS,
    AnthropicIngestOptions,
)


def _tool_stack_tier(tool_name: str, opts: AnthropicIngestOptions) -> StackTier:
    if tool_name in {"computer", "bash", "text_editor"}:
        return StackTier.CROSS_STACK
    if opts.cross_stack_tools_pattern and re.search(
        opts.cross_stack_tools_pattern, tool_name, re.IGNORECASE
    ):
        return StackTier.CROSS_STACK
    return opts.stack_tier


def _should_emit_state_mutation(
    tool_name: str,
    tool_input: Any,
    opts: AnthropicIngestOptions,
) -> bool:
    if tool_name == "computer":
        action = str((tool_input or {}).get("action") or "")
        return action in _COMPUTER_MUTATION_ACTIONS
    if tool_name == "bash":
        command = str((tool_input or {}).get("command") or (tool_input or {}).get("text") or "")
        return not re.search(opts.bash_readonly_pattern, command, re.IGNORECASE)
    if tool_name == "text_editor":
        action = str((tool_input or {}).get("action") or "")
        return action in _TEXT_EDITOR_MUTATION_ACTIONS
    if opts.state_mutation_tool_pattern:
        return re.search(opts.state_mutation_tool_pattern, tool_name, re.IGNORECASE) is not None
    return False


def _state_change_magnitude(tool_name: str, tool_input: Any) -> float:
    if tool_name == "computer":
        action = str((tool_input or {}).get("action") or "")
        return 0.0 if action == "screenshot" else 1.0
    if tool_name == "bash":
        return 1.0
    if tool_name == "text_editor":
        return 1.0
    return 1.0
