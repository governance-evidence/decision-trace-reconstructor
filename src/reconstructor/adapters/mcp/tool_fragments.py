"""MCP tool-call response fragments."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .fragment_common import (
    _client_actor,
    _fragment,
    _is_state_mutating_tool,
    _is_tool_error,
    _McpResponseContext,
)


def _tool_call_fragments(ctx: _McpResponseContext) -> list[Fragment]:
    params = dict(ctx.request_frame.get("params") or {})
    tool_name = str(params.get("name") or "")
    fragments = [_tool_call_fragment(ctx, params)]
    if _is_state_mutating_tool(tool_name, ctx.opts):
        fragments.append(_tool_state_fragment(ctx, tool_name))
    if _is_tool_error(ctx.response_frame):
        fragments.append(_tool_error_fragment(ctx))
    return fragments


def _tool_call_fragment(ctx: _McpResponseContext, params: dict[str, Any]) -> Fragment:
    return _fragment(
        f"mcp_{ctx.session_id}_{ctx.request_id}_tool_call",
        FragmentKind.TOOL_CALL,
        timestamp=float(ctx.request_entry["ts"]),
        actor_id=_client_actor(ctx.opts),
        payload={
            "tool_name": params.get("name"),
            "args": params.get("arguments") or {},
            "result": ctx.response_frame.get("result") or {},
        },
        parent_trace_id=ctx.session_id,
        decision_id_hint=ctx.session_id,
    )


def _tool_state_fragment(ctx: _McpResponseContext, tool_name: str) -> Fragment:
    return _fragment(
        f"mcp_{ctx.session_id}_{ctx.request_id}_tool_state",
        FragmentKind.STATE_MUTATION,
        timestamp=float(ctx.request_entry["ts"]) + 0.0001,
        actor_id=_client_actor(ctx.opts),
        payload={
            "event": f"state mutation via {tool_name}",
            "state_change_magnitude": 1.0,
        },
        parent_trace_id=ctx.session_id,
        decision_id_hint=ctx.session_id,
    )


def _tool_error_fragment(ctx: _McpResponseContext) -> Fragment:
    return _fragment(
        f"mcp_{ctx.session_id}_{ctx.request_id}_tool_error",
        FragmentKind.ERROR,
        timestamp=float(ctx.response_entry["ts"]),
        actor_id=_client_actor(ctx.opts),
        payload={"error": ctx.response_frame.get("error") or ctx.response_frame.get("result")},
        parent_trace_id=ctx.session_id,
        decision_id_hint=ctx.session_id,
    )
