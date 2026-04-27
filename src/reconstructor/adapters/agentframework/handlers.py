"""Agent Framework event dispatch facade."""

from __future__ import annotations

from collections.abc import Callable

from .activity_handlers import (
    _flush_pending as _flush_pending,
)
from .activity_handlers import (
    _handle_agent_called,
    _handle_agent_returned,
    _handle_model_invocation,
    _handle_model_response,
    _handle_tool_called,
    _handle_tool_returned,
)
from .common import _Event, _event_allowed
from .fragments import _actor_id, _override_kind
from .lifecycle_handlers import (
    _handle_content_safety_decision,
    _handle_error,
    _handle_message_published,
    _handle_round_completed,
    _handle_snapshot_override,
    _handle_speaker_selected,
    _handle_termination,
)
from .state import _AgentFrameworkState

_Handler = Callable[[_AgentFrameworkState, _Event, str], None]

_HANDLERS: dict[str, _Handler] = {
    "message_published": _handle_message_published,
    "agent_called": _handle_agent_called,
    "agent_returned": _handle_agent_returned,
    "tool_called": _handle_tool_called,
    "tool_returned": _handle_tool_returned,
    "model_invocation": _handle_model_invocation,
    "model_response": _handle_model_response,
    "speaker_selected": _handle_speaker_selected,
    "round_completed": _handle_round_completed,
    "termination": _handle_termination,
    "content_safety_decision": _handle_content_safety_decision,
    "error": _handle_error,
}


def _handle_event(state: _AgentFrameworkState, event: _Event) -> None:
    if not _event_allowed(event, state.cfg):
        return

    event_type = event["event_type"]
    actor_id = _actor_id(event, state.cfg)
    override_kind = _override_kind(event["payload"])

    if override_kind is not None and event_type != "content_safety_decision":
        _handle_snapshot_override(state, event, actor_id, override_kind)
        return

    handler = _HANDLERS.get(event_type)
    if handler is not None:
        handler(state, event, actor_id)


__all__ = ["_flush_pending", "_handle_event"]
