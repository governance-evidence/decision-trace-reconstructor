"""Message part dispatch for Pydantic AI run conversion."""

from __future__ import annotations

from typing import Any

from ...core.fragment import FragmentKind
from .fragments import _model_fragment
from .prompt_fragments import (
    _retry_error_fragment,
    _system_prompt_fragment,
    _user_prompt_fragment,
)
from .state import _PydanticAIRunState
from .tool_handlers import (
    _flush_pending_tools as _flush_pending_tools,
)
from .tool_handlers import (
    _handle_tool_return,
    _record_tool_call,
)


def _handle_message(
    state: _PydanticAIRunState,
    message: dict[str, Any],
    message_index: int,
) -> None:
    base_ts = float(message["timestamp"] or state.run_payload["ts_start"] or 0.0)
    if message["kind"] == "response":
        model_fragment = _model_fragment(
            state.run_payload,
            message,
            state.actor_id,
            state.opts,
            base_ts,
        )
        state.out.append(model_fragment)
        state.last_failure = (FragmentKind.MODEL_GENERATION, model_fragment.fragment_id)

    for part_index, part in enumerate(message["parts"]):
        _handle_part(state, message, message_index, part, part_index, base_ts)

    if message["kind"] == "response" and isinstance(state.out[-1].payload.get("text"), list):
        state.out[-1].payload["text"] = "\n".join(
            str(item) for item in state.out[-1].payload["text"] if item is not None
        )


def _handle_part(
    state: _PydanticAIRunState,
    message: dict[str, Any],
    message_index: int,
    part: dict[str, Any],
    part_index: int,
    base_ts: float,
) -> None:
    timestamp = float(part["timestamp"] or base_ts or state.run_payload["ts_start"] or 0.0)
    part_kind = part["part_kind"]

    if part_kind == "system-prompt":
        _handle_system_prompt(state, message, part, part_index, timestamp)
    elif part_kind == "user-prompt":
        state.out.append(_user_prompt_fragment(state, message, part, part_index, timestamp))
    elif part_kind == "thinking" and message["kind"] == "response":
        state.out[-1].payload["internal_reasoning"] = "opaque"
    elif part_kind == "text" and message["kind"] == "response":
        state.out[-1].payload.setdefault("text", [])
        state.out[-1].payload["text"].append(part.get("content"))
    elif part_kind == "tool-call":
        _record_tool_call(state, message_index, part_index, part, timestamp)
    elif part_kind == "tool-return":
        _handle_tool_return(state, part)
    elif part_kind == "retry-prompt":
        state.out.append(_retry_error_fragment(state, message, part, part_index, timestamp))


def _handle_system_prompt(
    state: _PydanticAIRunState,
    message: dict[str, Any],
    part: dict[str, Any],
    part_index: int,
    timestamp: float,
) -> None:
    if not state.opts.emit_system_prompt:
        return
    state.out.append(_system_prompt_fragment(state, message, part, part_index, timestamp))
