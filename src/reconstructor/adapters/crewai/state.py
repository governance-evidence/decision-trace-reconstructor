"""State container for CrewAI event handling."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from ...core.fragment import Fragment
from .common import CrewAIIngestOptions, _crew_name, _Event, _LogKey, _QueueKey


@dataclass
class _CrewAIState:
    cfg: CrewAIIngestOptions
    pending_tools: defaultdict[_QueueKey, deque[_Event]]
    pending_llm: defaultdict[_QueueKey, deque[_Event]]
    pending_memory: defaultdict[_QueueKey, deque[_Event]]
    pending_logs: defaultdict[_LogKey, list[str]]
    current_actor_by_crew: dict[str, str]
    out: list[Fragment]


def _new_state(cfg: CrewAIIngestOptions) -> _CrewAIState:
    pending_tools: defaultdict[_QueueKey, deque[_Event]] = defaultdict(deque)
    pending_llm: defaultdict[_QueueKey, deque[_Event]] = defaultdict(deque)
    pending_memory: defaultdict[_QueueKey, deque[_Event]] = defaultdict(deque)
    pending_logs: defaultdict[_LogKey, list[str]] = defaultdict(list)
    return _CrewAIState(
        cfg=cfg,
        pending_tools=pending_tools,
        pending_llm=pending_llm,
        pending_memory=pending_memory,
        pending_logs=pending_logs,
        current_actor_by_crew={},
        out=[],
    )


def _tool_key(event: _Event, actor_id: str) -> _QueueKey:
    payload = event["payload"]
    return (_crew_name(event), actor_id, str(payload.get("tool_name") or "tool_unknown"))


def _llm_key(event: _Event, actor_id: str) -> _QueueKey:
    payload = event["payload"]
    return (_crew_name(event), actor_id, str(payload.get("model") or "model_unknown"))


def _memory_key(event: _Event, actor_id: str) -> _QueueKey:
    payload = event["payload"]
    return (_crew_name(event), actor_id, str(payload.get("memory_type") or "memory"))
