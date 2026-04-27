"""MCP capability and initialization response fragments."""

from __future__ import annotations

from ...core.fragment import Fragment, FragmentKind
from .fragment_common import _fragment, _McpResponseContext, _server_actor


def _initialize_fragment(ctx: _McpResponseContext) -> Fragment:
    result = dict(ctx.response_frame.get("result") or {})
    server_info = dict(result.get("serverInfo") or {})
    ctx.session["server_name"] = server_info.get("name") or ctx.session.get("server_name")
    return _fragment(
        f"mcp_{ctx.session_id}_{ctx.request_id}_initialize",
        FragmentKind.CONFIG_SNAPSHOT,
        timestamp=float(ctx.response_entry["ts"]),
        actor_id=_server_actor(ctx.session, ctx.opts, ctx.session_id),
        payload={
            "server_name": server_info.get("name"),
            "server_version": server_info.get("version"),
            "capabilities": result.get("capabilities") or {},
            "protocol_version": result.get("protocolVersion")
            or (ctx.request_frame.get("params") or {}).get("protocolVersion"),
            "transport": ctx.response_entry.get("transport"),
        },
        parent_trace_id=ctx.session_id,
        decision_id_hint=ctx.session_id,
    )


def _tools_list_fragments(ctx: _McpResponseContext) -> list[Fragment]:
    if not ctx.opts.emit_tools_list:
        return []
    return [
        _fragment(
            f"mcp_{ctx.session_id}_{ctx.request_id}_tools_list",
            FragmentKind.CONFIG_SNAPSHOT,
            timestamp=float(ctx.response_entry["ts"]),
            actor_id=_server_actor(ctx.session, ctx.opts, ctx.session_id),
            payload={
                "tools": (ctx.response_frame.get("result") or {}).get("tools") or [],
                "server_name": ctx.session.get("server_name"),
            },
            parent_trace_id=ctx.session_id,
            decision_id_hint=ctx.session_id,
        )
    ]
