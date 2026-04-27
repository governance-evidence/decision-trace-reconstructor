"""Bedrock trace fragment context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.fragment import StackTier
from .common import BedrockIngestOptions, _actor_id, _trace_id_from_block


@dataclass(frozen=True)
class _BedrockEventContext:
    session: dict[str, Any]
    block: dict[str, Any]
    opts: BedrockIngestOptions
    trace_type: str
    timestamp: float
    actor_id: str
    parent_trace_id: str | None
    decision_id_hint: str
    stack_tier: StackTier

    @property
    def session_id(self) -> str:
        return str(self.session["session_id"])


def _event_context(
    event: dict[str, Any],
    session: dict[str, Any],
    opts: BedrockIngestOptions,
) -> _BedrockEventContext:
    block = event["block"]
    return _BedrockEventContext(
        session=session,
        block=block,
        opts=opts,
        trace_type=event["trace_type"],
        timestamp=float(event["timestamp"]),
        actor_id=_actor_id(session, opts, block),
        parent_trace_id=_trace_id_from_block(block),
        decision_id_hint=session["session_id"],
        stack_tier=opts.stack_tier,
    )
