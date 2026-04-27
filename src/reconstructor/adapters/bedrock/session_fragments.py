"""Bedrock session-level fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import (
    BedrockIngestOptions,
    _actor_id,
    _content_field,
    _fragment,
    _fragment_id,
    _memory_summaries,
)
from .trace_fragments import _event_to_fragments


def _session_to_fragments(session: dict[str, Any], opts: BedrockIngestOptions) -> list[Fragment]:
    session_id = session["session_id"]
    actor_id = _actor_id(session, opts)
    out: list[Fragment] = [
        Fragment(
            fragment_id=_fragment_id(session_id, "config"),
            timestamp=float(session["_ts"]),
            kind=FragmentKind.CONFIG_SNAPSHOT,
            stack_tier=opts.stack_tier,
            actor_id=actor_id,
            payload={
                "agent_id": session.get("agent_id"),
                "agent_alias_id": session.get("agent_alias_id"),
                "agent_version": session.get("agent_version"),
                "foundation_model": session.get("foundation_model"),
            },
            decision_id_hint=session_id,
        )
    ]
    out.extend(_memory_fragments(session, opts, actor_id))
    for event in session.get("events", []):
        out.extend(_event_to_fragments(event, session, opts))
    return out


def _memory_fragments(
    session: dict[str, Any],
    opts: BedrockIngestOptions,
    actor_id: str,
) -> list[Fragment]:
    memory_id = session.get("memory_id")
    if not memory_id:
        return []

    out: list[Fragment] = []
    session_id = session["session_id"]
    base_ts = float(session["_ts"])
    memory_contents = session.get("memory_contents") or []
    if memory_contents:
        summaries = _memory_summaries(memory_contents)
        if summaries:
            out.append(
                _fragment(
                    _fragment_id(session_id, "memory_retrieval", base_ts + 0.0001),
                    FragmentKind.RETRIEVAL_RESULT,
                    timestamp=base_ts + 0.0001,
                    stack_tier=opts.stack_tier,
                    actor_id=actor_id,
                    parent_trace_id=None,
                    decision_id_hint=session_id,
                    payload={
                        "query": {"memory_id": memory_id, "memory_type": "SESSION_SUMMARY"},
                        "retrieved": _content_field(summaries, opts.store_content),
                    },
                )
            )

    memory_summary = session.get("memory_summary")
    if isinstance(memory_summary, dict) and memory_summary:
        out.append(
            _fragment(
                _fragment_id(session_id, "memory_write", base_ts + 0.0002),
                FragmentKind.STATE_MUTATION,
                timestamp=base_ts + 0.0002,
                stack_tier=opts.stack_tier,
                actor_id=actor_id,
                parent_trace_id=None,
                decision_id_hint=session_id,
                payload={
                    "state_change_magnitude": 1.0,
                    "event": f"memory summary persisted for {memory_id}",
                    "memory_id": memory_id,
                    "summary": _content_field(memory_summary, opts.store_content),
                },
            )
        )
    return out
