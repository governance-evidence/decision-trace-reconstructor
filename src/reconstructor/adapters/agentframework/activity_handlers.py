"""Agent Framework handlers for paired activity events with pending queues."""

from __future__ import annotations

from .common import _Event, _matches
from .fragments import (
    _actor_id,
    _agent_fragment,
    _model_fragment,
    _state_fragment,
    _tool_fragment,
)
from .state import (
    _agent_key,
    _AgentFrameworkState,
    _append_with_round_context,
    _model_key,
    _tool_key,
)


def _handle_agent_called(state: _AgentFrameworkState, event: _Event, _actor_id: str) -> None:
    state.pending_agents[_agent_key(event)].append(event)


def _handle_agent_returned(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    agent_key = _agent_key(event)
    start = state.pending_agents[agent_key].popleft() if state.pending_agents[agent_key] else None
    fragment = _agent_fragment(start or event, event if start else None, actor_id, state.cfg)
    _append_with_round_context(state, fragment, event["trace_id"])


def _handle_tool_called(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    state.pending_tools[_tool_key(event, actor_id)].append(event)


def _handle_tool_returned(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    payload = event["payload"]
    tool_key = _tool_key(event, actor_id)
    start = state.pending_tools[tool_key].popleft() if state.pending_tools[tool_key] else None
    fragment = _tool_fragment(start or event, event if start else None, actor_id, state.cfg)
    _append_with_round_context(state, fragment, event["trace_id"])
    if _matches(payload.get("tool_name"), state.cfg.state_mutation_tool_pattern):
        state.out.append(_state_fragment(start or event, actor_id, state.cfg))


def _handle_model_invocation(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    state.pending_models[_model_key(event, actor_id)].append(event)


def _handle_model_response(state: _AgentFrameworkState, event: _Event, actor_id: str) -> None:
    model_key = _model_key(event, actor_id)
    start = state.pending_models[model_key].popleft() if state.pending_models[model_key] else None
    fragment = _model_fragment(start or event, event if start else None, actor_id, state.cfg)
    _append_with_round_context(state, fragment, event["trace_id"])


def _flush_pending(state: _AgentFrameworkState) -> None:
    for queue in state.pending_agents.values():
        while queue:
            start = queue.popleft()
            actor_id = _actor_id(start, state.cfg)
            fragment = _agent_fragment(start, None, actor_id, state.cfg)
            _append_with_round_context(state, fragment, start["trace_id"])

    for queue in state.pending_tools.values():
        while queue:
            start = queue.popleft()
            actor_id = _actor_id(start, state.cfg)
            fragment = _tool_fragment(start, None, actor_id, state.cfg)
            _append_with_round_context(state, fragment, start["trace_id"])
            if _matches(start["payload"].get("tool_name"), state.cfg.state_mutation_tool_pattern):
                state.out.append(_state_fragment(start, actor_id, state.cfg))

    for queue in state.pending_models.values():
        while queue:
            start = queue.popleft()
            actor_id = _actor_id(start, state.cfg)
            fragment = _model_fragment(start, None, actor_id, state.cfg)
            _append_with_round_context(state, fragment, start["trace_id"])
