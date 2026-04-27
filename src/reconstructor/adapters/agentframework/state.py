"""Agent Framework event handling state."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from ...core.fragment import Fragment
from .common import AgentFrameworkIngestOptions, _AgentKey, _Event, _QueueKey
from .fragments import _agent_scope, _attach_round_context


@dataclass
class _AgentFrameworkState:
    cfg: AgentFrameworkIngestOptions
    pending_agents: defaultdict[_AgentKey, deque[_Event]]
    pending_tools: defaultdict[_QueueKey, deque[_Event]]
    pending_models: defaultdict[_QueueKey, deque[_Event]]
    pending_rounds: dict[str, _Event]
    out: list[Fragment]


def _new_state(cfg: AgentFrameworkIngestOptions) -> _AgentFrameworkState:
    pending_agents: defaultdict[_AgentKey, deque[_Event]] = defaultdict(deque)
    pending_tools: defaultdict[_QueueKey, deque[_Event]] = defaultdict(deque)
    pending_models: defaultdict[_QueueKey, deque[_Event]] = defaultdict(deque)
    return _AgentFrameworkState(
        cfg=cfg,
        pending_agents=pending_agents,
        pending_tools=pending_tools,
        pending_models=pending_models,
        pending_rounds={},
        out=[],
    )


def _append_with_round_context(
    state: _AgentFrameworkState,
    fragment: Fragment,
    trace_id: str,
) -> None:
    _attach_round_context(fragment, state.pending_rounds.pop(trace_id, None))
    state.out.append(fragment)


def _agent_key(event: _Event) -> _AgentKey:
    return (event["trace_id"], _agent_scope(event["payload"], event))


def _tool_key(event: _Event, actor_id: str) -> _QueueKey:
    payload = event["payload"]
    return (event["trace_id"], actor_id, str(payload.get("tool_name") or "tool_unknown"))


def _model_key(event: _Event, actor_id: str) -> _QueueKey:
    payload = event["payload"]
    return (event["trace_id"], actor_id, str(payload.get("model") or "model_unknown"))
