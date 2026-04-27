"""CrewAI handlers for paired activity events with pending queues."""

from __future__ import annotations

from .common import _crew_name, _Event, _matches
from .fragments import (
    _actor_id,
    _error_fragment,
    _llm_fragment,
    _memory_fragment,
    _tool_fragment,
    _tool_state_fragment,
)
from .state import _CrewAIState, _llm_key, _memory_key, _tool_key


def _handle_tool_usage_started(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    state.pending_tools[_tool_key(event, actor_id)].append(event)


def _handle_tool_usage_finished(state: _CrewAIState, event: _Event) -> None:
    payload = event["payload"]
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    tool_key = _tool_key(event, actor_id)
    start = state.pending_tools[tool_key].popleft() if state.pending_tools[tool_key] else None
    state.out.append(_tool_fragment(start or event, event, actor_id, state.cfg, error=None))
    if _matches(payload.get("tool_name"), state.cfg.state_mutation_tool_pattern):
        state.out.append(_tool_state_fragment(start or event, actor_id, state.cfg))


def _handle_tool_usage_error(state: _CrewAIState, event: _Event) -> None:
    payload = event["payload"]
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    tool_key = _tool_key(event, actor_id)
    start = state.pending_tools[tool_key].popleft() if state.pending_tools[tool_key] else None
    state.out.append(
        _tool_fragment(start or event, None, actor_id, state.cfg, error=payload.get("error"))
    )
    state.out.append(
        _error_fragment(event, actor_id, state.cfg, payload.get("error"), suffix="tool_error")
    )
    if _matches(payload.get("tool_name"), state.cfg.state_mutation_tool_pattern):
        state.out.append(_tool_state_fragment(start or event, actor_id, state.cfg))


def _handle_llm_call_started(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    state.pending_llm[_llm_key(event, actor_id)].append(event)


def _handle_llm_call_completed(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    llm_key = _llm_key(event, actor_id)
    start = state.pending_llm[llm_key].popleft() if state.pending_llm[llm_key] else None
    state.out.append(
        _llm_fragment(
            start or event,
            event if start else None,
            actor_id,
            state.cfg,
            state.pending_logs.get((crew_name, actor_id), []),
        )
    )
    state.pending_logs[(crew_name, actor_id)].clear()


def _handle_agent_log(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.pending_logs[(crew_name, actor_id)].append(str(event["payload"].get("text") or ""))


def _handle_memory_query_started(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    state.pending_memory[_memory_key(event, actor_id)].append(event)


def _handle_memory_query_completed(state: _CrewAIState, event: _Event) -> None:
    crew_name = _crew_name(event)
    actor_id = _actor_id(event, state.current_actor_by_crew.get(crew_name), state.cfg)
    state.current_actor_by_crew[crew_name] = actor_id
    memory_key = _memory_key(event, actor_id)
    start = state.pending_memory[memory_key].popleft() if state.pending_memory[memory_key] else None
    state.out.append(
        _memory_fragment(start or event, event if start else None, actor_id, state.cfg)
    )


def _flush_pending(state: _CrewAIState) -> None:
    for tool_queue in state.pending_tools.values():
        while tool_queue:
            start = tool_queue.popleft()
            actor_id = _actor_id(start, None, state.cfg)
            state.out.append(_tool_fragment(start, None, actor_id, state.cfg, error=None))
            if _matches(start["payload"].get("tool_name"), state.cfg.state_mutation_tool_pattern):
                state.out.append(_tool_state_fragment(start, actor_id, state.cfg))

    for llm_key, llm_queue in state.pending_llm.items():
        crew_name, actor_id, _model = llm_key
        while llm_queue:
            start = llm_queue.popleft()
            state.out.append(
                _llm_fragment(
                    start,
                    None,
                    actor_id,
                    state.cfg,
                    state.pending_logs.get((crew_name, actor_id), []),
                )
            )
            state.pending_logs[(crew_name, actor_id)].clear()

    for memory_queue in state.pending_memory.values():
        while memory_queue:
            start = memory_queue.popleft()
            actor_id = _actor_id(start, None, state.cfg)
            state.out.append(_memory_fragment(start, None, actor_id, state.cfg))
