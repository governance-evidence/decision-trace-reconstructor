"""Shared MCP fragment context and low-level builders."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import McpIngestOptions


@dataclass(frozen=True)
class _McpResponseContext:
    response_entry: dict[str, Any]
    request_entry: dict[str, Any]
    session: dict[str, Any]
    opts: McpIngestOptions
    request_frame: dict[str, Any]
    response_frame: dict[str, Any]
    method: str
    request_id: str
    session_id: str


def _mcp_response_context(
    response_entry: dict[str, Any],
    request_entry: dict[str, Any],
    session: dict[str, Any],
    opts: McpIngestOptions,
) -> _McpResponseContext:
    request_frame = request_entry["frame"]
    response_frame = response_entry["frame"]
    return _McpResponseContext(
        response_entry=response_entry,
        request_entry=request_entry,
        session=session,
        opts=opts,
        request_frame=request_frame,
        response_frame=response_frame,
        method=str(request_frame.get("method") or ""),
        request_id=str(request_frame.get("id")),
        session_id=request_entry["session_id"],
    )


def _is_state_mutating_tool(tool_name: str, opts: McpIngestOptions) -> bool:
    return bool(
        opts.state_mutation_tool_pattern
        and re.search(opts.state_mutation_tool_pattern, tool_name, re.IGNORECASE)
    )


def _is_tool_error(response_frame: dict[str, Any]) -> bool:
    return bool(response_frame.get("error") or (response_frame.get("result") or {}).get("isError"))


def _client_actor(opts: McpIngestOptions) -> str:
    return opts.actor_override or "mcp_client"


def _server_actor(session: dict[str, Any], opts: McpIngestOptions, session_id: str) -> str:
    return str(session.get("server_name") or opts.actor_override or f"mcp_server_{session_id[:8]}")


def _uri_value(uri: Any, store_uris: bool) -> Any:
    if store_uris:
        return uri
    text = "" if uri is None else str(uri)
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "length": len(text)}


def _fragment(
    fragment_id: str,
    kind: FragmentKind,
    *,
    timestamp: float,
    actor_id: str,
    payload: dict[str, Any],
    parent_trace_id: str | None,
    decision_id_hint: str | None,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=kind,
        stack_tier=StackTier.CROSS_STACK,
        actor_id=actor_id,
        payload=payload,
        parent_trace_id=parent_trace_id,
        decision_id_hint=decision_id_hint,
    )
