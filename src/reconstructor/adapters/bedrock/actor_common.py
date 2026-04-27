"""Shared Bedrock actor and trace helpers."""

from __future__ import annotations

from typing import Any

from .options import BedrockIngestOptions


def _actor_id(
    session: dict[str, Any],
    opts: BedrockIngestOptions,
    block: dict[str, Any] | None = None,
) -> str:
    if opts.actor_override:
        return opts.actor_override
    block = block or {}
    collaborator = block.get("agentCollaboratorInvocationInput") or {}
    if isinstance(collaborator, dict) and collaborator.get("collaboratorName"):
        return str(collaborator["collaboratorName"])
    for value in (session.get("agent_alias_id"), session.get("agent_id")):
        if value:
            return str(value)
    return f"agent_{str(session['session_id'])[:8]}"


def _trace_id_from_block(block: dict[str, Any]) -> str | None:
    if block.get("traceId"):
        return str(block["traceId"])
    for value in block.values():
        if isinstance(value, dict) and value.get("traceId"):
            return str(value["traceId"])
    return None
