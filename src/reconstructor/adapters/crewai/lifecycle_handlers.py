"""CrewAI lifecycle, coordination, and policy event handlers."""

from __future__ import annotations

from .common import _crew_name, _Event
from .fragments import (
    _actor_id,
    _config_fragment,
    _error_fragment,
    _message_fragment,
    _policy_fragment,
)
from .state import _CrewAIState


def _handle_crew_kickoff_started(state: _CrewAIState, event: _Event) -> None:
    if not state.cfg.emit_config_snapshot:
        return
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.out.append(_config_fragment(event, actor_id, state.cfg))


def _handle_agent_execution_started(state: _CrewAIState, event: _Event) -> None:
    payload = event["payload"]
    crew_name = _crew_name(event)
    actor_id = str(
        payload.get("agent_role")
        or payload.get("assigned_agent")
        or _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    )
    state.current_actor_by_crew[crew_name] = actor_id
    state.out.append(
        _message_fragment(
            event,
            actor_id,
            state.cfg,
            suffix="agent_execution",
            payload_extra={
                "task_id": payload.get("task_id"),
                "task_description": payload.get("task_description"),
                "tools": payload.get("tools") or [],
            },
        )
    )


def _handle_task_started(state: _CrewAIState, event: _Event) -> None:
    payload = event["payload"]
    crew_name = _crew_name(event)
    actor_id = str(
        payload.get("assigned_agent")
        or _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    )
    state.current_actor_by_crew[crew_name] = actor_id
    state.out.append(
        _message_fragment(
            event,
            actor_id,
            state.cfg,
            suffix="task_started",
            payload_extra={
                "task_id": payload.get("task_id"),
                "task_description": payload.get("task_description"),
                "expected_output": payload.get("expected_output"),
                "human_input": bool(payload.get("human_input")),
                "static_assignment": True,
            },
        )
    )


def _handle_delegation(state: _CrewAIState, event: _Event) -> None:
    payload = event["payload"]
    crew_name = _crew_name(event)
    actor_id = str(
        payload.get("from_agent")
        or _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    )
    state.out.append(
        _message_fragment(
            event,
            actor_id,
            state.cfg,
            suffix="delegation",
            payload_extra={
                "delegation": True,
                "from_agent": payload.get("from_agent"),
                "to_agent": payload.get("to_agent"),
                "task": payload.get("task"),
            },
        )
    )
    if payload.get("to_agent"):
        state.current_actor_by_crew[crew_name] = str(payload["to_agent"])


def _handle_manager_agent_invoked(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    payload = event["payload"]
    state.current_actor_by_crew[crew_name] = "Manager"
    state.out.append(
        _message_fragment(
            event,
            "Manager",
            state.cfg,
            suffix="manager_invoked",
            payload_extra={
                "manager": True,
                "task": payload.get("task"),
            },
        )
    )


def _handle_consensual_vote_cast(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    payload = event["payload"]
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    state.out.append(
        _message_fragment(
            event,
            actor_id,
            state.cfg,
            suffix="vote",
            payload_extra={
                "vote": payload.get("vote"),
                "proposal": payload.get("proposal"),
            },
        )
    )


def _handle_policy_snapshot(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.out.append(_policy_fragment(event, actor_id, state.cfg))


def _handle_scope_error(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.out.append(
        _error_fragment(
            event,
            actor_id,
            state.cfg,
            event["payload"].get("error"),
            suffix="scope_error",
        )
    )
