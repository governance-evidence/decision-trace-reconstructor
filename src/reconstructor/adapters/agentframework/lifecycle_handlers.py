"""Agent Framework handlers for control and lifecycle events."""

from __future__ import annotations

from ...core.fragment import FragmentKind
from .common import _Event
from .fragments import (
    _error_fragment,
    _message_fragment,
    _snapshot_fragment,
)
from .state import _AgentFrameworkState, _append_with_round_context


def _handle_snapshot_override(
    state: _AgentFrameworkState,
    event: _Event,
    actor_id: str,
    override_kind: FragmentKind,
) -> None:
    _append_with_round_context(
        state,
        _snapshot_fragment(event, actor_id, state.cfg, override_kind),
        event["trace_id"],
    )


def _handle_message_published(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    payload = event["payload"]
    fragment = _message_fragment(
        event,
        actor_id,
        state.cfg,
        suffix="published",
        payload={
            "content": payload.get("content"),
            "topic": event.get("topic"),
            "recipient": event.get("recipient"),
        },
    )
    _append_with_round_context(state, fragment, event["trace_id"])


def _handle_speaker_selected(state: _AgentFrameworkState, event: _Event, _actor_id: str) -> None:
    payload = event["payload"]
    fragment = _message_fragment(
        event,
        "manager",
        state.cfg,
        suffix="speaker_selected",
        payload={
            "role": "speaker_select",
            "selected": payload.get("selected"),
            "candidates": payload.get("candidates") or [],
        },
    )
    _append_with_round_context(state, fragment, event["trace_id"])


def _handle_round_completed(state: _AgentFrameworkState, event: _Event, _actor_id: str) -> None:
    payload = event["payload"]
    state.pending_rounds[event["trace_id"]] = {
        "round_num": payload.get("round_num"),
        "messages_in_round": payload.get("messages_in_round"),
    }


def _handle_termination(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    payload = event["payload"]
    fragment = _message_fragment(
        event,
        actor_id,
        state.cfg,
        suffix="termination",
        payload={
            "terminal": True,
            "reason": payload.get("reason"),
        },
    )
    _append_with_round_context(state, fragment, event["trace_id"])


def _handle_content_safety_decision(
    state: _AgentFrameworkState, event: _Event, actor_id: str
) -> None:
    fragment = _snapshot_fragment(event, actor_id, state.cfg, FragmentKind.POLICY_SNAPSHOT)
    fragment.payload.setdefault("constraint_activated", True)
    _append_with_round_context(state, fragment, event["trace_id"])


def _handle_error(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    _append_with_round_context(
        state,
        _error_fragment(event, actor_id, state.cfg),
        event["trace_id"],
    )
