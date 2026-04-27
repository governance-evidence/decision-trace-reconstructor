"""Tool lifecycle handlers for Pydantic AI run conversion."""

from __future__ import annotations

from typing import Any

from ...core.fragment import FragmentKind
from .common import _matches
from .fragments import _state_fragment, _takeover_fragment, _tool_fragment
from .state import _PydanticAIRunState


def _record_tool_call(
    state: _PydanticAIRunState,
    message_index: int,
    part_index: int,
    part: dict[str, Any],
    timestamp: float,
) -> None:
    tool_name = str(part.get("tool_name") or "tool_unknown")
    tool_call_id = str(part.get("tool_call_id") or f"tool_call_{message_index}_{part_index}")
    state.pending_tools[tool_call_id] = {
        "tool_name": tool_name,
        "args": dict(part.get("args") or {}),
        "timestamp": timestamp,
        "tool_def": state.tool_defs.get(tool_name) or {},
    }


def _handle_tool_return(state: _PydanticAIRunState, part: dict[str, Any]) -> None:
    tool_call_id = str(part.get("tool_call_id") or "")
    tool_record = state.pending_tools.pop(tool_call_id, None)
    if tool_record is None:
        return
    tool_fragment = _tool_fragment(state.run_payload, tool_record, part, state.opts)
    state.out.append(tool_fragment)
    state.last_failure = (FragmentKind.TOOL_CALL, tool_fragment.fragment_id)
    if _matches(tool_record["tool_name"], state.opts.state_mutation_tool_pattern):
        state.out.append(_state_fragment(state.run_payload, tool_record, state.opts))
    hitl_fragment = _takeover_fragment(state.run_payload, tool_record, part, state.opts)
    if hitl_fragment is not None:
        state.out.append(hitl_fragment)


def _flush_pending_tools(state: _PydanticAIRunState) -> None:
    for tool_record in state.pending_tools.values():
        state.out.append(_tool_fragment(state.run_payload, tool_record, None, state.opts))
        if _matches(tool_record["tool_name"], state.opts.state_mutation_tool_pattern):
            state.out.append(_state_fragment(state.run_payload, tool_record, state.opts))
