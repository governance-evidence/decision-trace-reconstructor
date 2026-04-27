"""CrewAI event dispatch facade."""

from __future__ import annotations

from .activity_handlers import (
    _handle_agent_log,
    _handle_llm_call_completed,
    _handle_llm_call_started,
    _handle_memory_query_completed,
    _handle_memory_query_started,
    _handle_tool_usage_error,
    _handle_tool_usage_finished,
    _handle_tool_usage_started,
)
from .common import _SKIPPED_EVENT_TYPES, _Event
from .lifecycle_handlers import (
    _handle_agent_execution_started,
    _handle_consensual_vote_cast,
    _handle_crew_kickoff_started,
    _handle_delegation,
    _handle_manager_agent_invoked,
    _handle_policy_snapshot,
    _handle_scope_error,
    _handle_task_started,
)
from .state import _CrewAIState

_HANDLERS = {
    "crew_kickoff_started": _handle_crew_kickoff_started,
    "agent_execution_started": _handle_agent_execution_started,
    "task_started": _handle_task_started,
    "tool_usage_started": _handle_tool_usage_started,
    "tool_usage_finished": _handle_tool_usage_finished,
    "tool_usage_error": _handle_tool_usage_error,
    "llm_call_started": _handle_llm_call_started,
    "llm_call_completed": _handle_llm_call_completed,
    "agent_logs_execution": _handle_agent_log,
    "memory_query_started": _handle_memory_query_started,
    "memory_query_completed": _handle_memory_query_completed,
    "delegation": _handle_delegation,
    "manager_agent_invoked": _handle_manager_agent_invoked,
    "consensual_vote_cast": _handle_consensual_vote_cast,
    "demm_policy_snapshot": _handle_policy_snapshot,
}

_ERROR_EVENT_TYPES = {"crew_kickoff_failed", "agent_execution_failed", "task_failed"}


def _handle_event(state: _CrewAIState, event: _Event) -> None:
    event_type = event["event_type"]
    if event_type in _SKIPPED_EVENT_TYPES:
        return
    handler = _HANDLERS.get(event_type)
    if handler is not None:
        handler(state, event)
        return
    if event_type in _ERROR_EVENT_TYPES:
        _handle_scope_error(state, event)
