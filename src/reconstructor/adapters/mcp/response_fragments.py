"""MCP request/response pair fragment dispatch."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from .capability_fragments import _initialize_fragment, _tools_list_fragments
from .common import McpIngestOptions
from .fragment_common import _mcp_response_context
from .resource_prompt_fragments import _prompt_get_fragment, _resource_read_fragment
from .tool_fragments import _tool_call_fragments


def _response_to_fragments(
    response_entry: dict[str, Any],
    request_entry: dict[str, Any],
    session: dict[str, Any],
    opts: McpIngestOptions,
) -> list[Fragment]:
    ctx = _mcp_response_context(response_entry, request_entry, session, opts)
    if ctx.method == "initialize":
        return [_initialize_fragment(ctx)]
    if ctx.method == "tools/list":
        return _tools_list_fragments(ctx)
    if ctx.method == "tools/call":
        return _tool_call_fragments(ctx)
    if ctx.method == "resources/read":
        return [_resource_read_fragment(ctx)]
    if ctx.method == "prompts/get":
        return [_prompt_get_fragment(ctx)]
    return []


__all__ = ["_response_to_fragments"]
