"""State helpers for Pydantic AI run conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import PydanticAIIngestOptions
from .fragments import _actor_id


@dataclass
class _PydanticAIRunState:
    run_payload: dict[str, Any]
    opts: PydanticAIIngestOptions
    actor_id: str
    tool_defs: dict[str, dict[str, Any]]
    pending_tools: dict[str, dict[str, Any]]
    last_failure: tuple[FragmentKind, str] | None
    out: list[Fragment]


def _new_run_state(
    run_payload: dict[str, Any],
    opts: PydanticAIIngestOptions,
) -> _PydanticAIRunState:
    actor_id = _actor_id(run_payload, opts)
    tool_defs = {str(tool["tool_name"]): tool for tool in run_payload["tools"]}
    return _PydanticAIRunState(
        run_payload=run_payload,
        opts=opts,
        actor_id=actor_id,
        tool_defs=tool_defs,
        pending_tools={},
        last_failure=None,
        out=[],
    )
