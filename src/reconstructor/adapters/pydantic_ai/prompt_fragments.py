"""Pydantic AI prompt and retry fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .fragments import _fragment
from .state import _PydanticAIRunState


def _system_prompt_fragment(
    state: _PydanticAIRunState,
    message: dict[str, Any],
    part: dict[str, Any],
    part_index: int,
    timestamp: float,
) -> Fragment:
    return _fragment(
        state.run_payload,
        fragment_id=f"pydantic_ai_{state.run_payload['run_id']}_{message['message_id']}_system_{part_index + 1}",
        timestamp=timestamp,
        kind=FragmentKind.CONFIG_SNAPSHOT,
        stack_tier=state.opts.stack_tier,
        actor_id=state.actor_id,
        payload={"system_prompt": part.get("content")},
    )


def _user_prompt_fragment(
    state: _PydanticAIRunState,
    message: dict[str, Any],
    part: dict[str, Any],
    part_index: int,
    timestamp: float,
) -> Fragment:
    return _fragment(
        state.run_payload,
        fragment_id=f"pydantic_ai_{state.run_payload['run_id']}_{message['message_id']}_user_{part_index + 1}",
        timestamp=timestamp,
        kind=FragmentKind.AGENT_MESSAGE,
        stack_tier=state.opts.stack_tier,
        actor_id=state.actor_id,
        payload={"content": part.get("content"), "role": "user"},
    )


def _retry_error_fragment(
    state: _PydanticAIRunState,
    message: dict[str, Any],
    part: dict[str, Any],
    part_index: int,
    timestamp: float,
) -> Fragment:
    error_payload = {
        "error": part.get("content"),
        "failed_fragment_kind": state.last_failure[0].value if state.last_failure else None,
        "failed_fragment_id": state.last_failure[1] if state.last_failure else None,
    }
    return _fragment(
        state.run_payload,
        fragment_id=f"pydantic_ai_{state.run_payload['run_id']}_{message['message_id']}_retry_{part_index + 1}",
        timestamp=timestamp,
        kind=FragmentKind.ERROR,
        stack_tier=state.opts.stack_tier,
        actor_id=state.actor_id,
        payload=error_payload,
    )
