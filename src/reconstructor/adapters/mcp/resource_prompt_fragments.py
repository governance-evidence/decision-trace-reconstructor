"""MCP resource and prompt response fragments."""

from __future__ import annotations

from ...core.fragment import Fragment, FragmentKind
from .fragment_common import _client_actor, _fragment, _McpResponseContext, _uri_value


def _resource_read_fragment(ctx: _McpResponseContext) -> Fragment:
    params = dict(ctx.request_frame.get("params") or {})
    uri = params.get("uri")
    return _fragment(
        f"mcp_{ctx.session_id}_{ctx.request_id}_resource_read",
        FragmentKind.RETRIEVAL_RESULT,
        timestamp=float(ctx.response_entry["ts"]),
        actor_id=_client_actor(ctx.opts),
        payload={
            "query": _uri_value(uri, ctx.opts.store_uris),
            "retrieved": (ctx.response_frame.get("result") or {}).get("contents") or [],
        },
        parent_trace_id=ctx.session_id,
        decision_id_hint=ctx.session_id,
    )


def _prompt_get_fragment(ctx: _McpResponseContext) -> Fragment:
    params = dict(ctx.request_frame.get("params") or {})
    result = dict(ctx.response_frame.get("result") or {})
    return _fragment(
        f"mcp_{ctx.session_id}_{ctx.request_id}_prompt_get",
        FragmentKind.AGENT_MESSAGE,
        timestamp=float(ctx.response_entry["ts"]),
        actor_id=_client_actor(ctx.opts),
        payload={
            "prompt_name": params.get("name"),
            "arguments": params.get("arguments") or {},
            "messages": result.get("messages") or [],
            "description": result.get("description"),
        },
        parent_trace_id=ctx.session_id,
        decision_id_hint=ctx.session_id,
    )
