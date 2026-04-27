"""Shared Bedrock tool classification helpers."""

from __future__ import annotations

import re
from typing import Any

from ...core.fragment import StackTier
from .fragment_common import _content_field
from .options import BedrockIngestOptions


def _action_group_tool_name(action_group: dict[str, Any]) -> str:
    name = str(action_group.get("actionGroupName") or "action_group")
    path = action_group.get("apiPath") or action_group.get("functionName")
    return f"{name}:{path}" if path else name


def _orchestration_tool_invocation(
    invocation_input: dict[str, Any],
    store_content: bool,
) -> dict[str, Any] | None:
    action_group = invocation_input.get("actionGroupInvocationInput") or {}
    if action_group:
        action_group_args = {
            "parameters": action_group.get("parameters"),
            "requestBody": action_group.get("requestBody"),
        }
        if action_group.get("functionName") is not None:
            action_group_args["function"] = action_group.get("functionName")
        return {
            "tool_name": _action_group_tool_name(action_group),
            "args": _content_field(action_group_args, store_content),
            "verb": action_group.get("verb"),
            "force_state_mutation": False,
        }

    code_interpreter = invocation_input.get("codeInterpreterInvocationInput") or {}
    if code_interpreter:
        return {
            "tool_name": "code_interpreter",
            "args": _content_field(code_interpreter, store_content),
            "verb": "EXECUTE",
            "force_state_mutation": True,
        }

    return None


def _tool_stack_tier(tool_name: str, opts: BedrockIngestOptions) -> StackTier:
    if tool_name.split(":", 1)[0] in set(opts.cross_stack_action_groups):
        return StackTier.CROSS_STACK
    return opts.stack_tier


def _is_state_mutation(
    tool_name: str,
    verb: Any,
    opts: BedrockIngestOptions,
    *,
    force: bool = False,
) -> bool:
    if force:
        return True
    if str(verb or "").upper() in {"POST", "PUT", "DELETE", "PATCH"}:
        return True
    if opts.state_mutation_tool_pattern and re.search(
        opts.state_mutation_tool_pattern, tool_name, re.IGNORECASE
    ):
        return True
    return False
