"""MCP standalone request and notification fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import McpIngestOptions
from .fragment_common import _fragment, _server_actor, _uri_value


def _sampling_fragment(
    entry: dict[str, Any], session: dict[str, Any], opts: McpIngestOptions
) -> Fragment:
    frame = entry["frame"]
    params = dict(frame.get("params") or {})
    session_id = entry["session_id"]
    request_id = str(frame.get("id"))
    return _fragment(
        f"mcp_{session_id}_{request_id}_sampling",
        FragmentKind.MODEL_GENERATION,
        timestamp=float(entry["ts"]),
        actor_id=_server_actor(session, opts, session_id),
        payload={
            "model_id": params.get("modelPreferences") or "mcp_sampling_request",
            "internal_reasoning": "opaque",
            "messages": params.get("messages") or [],
            "system_prompt": params.get("systemPrompt"),
            "partial": True,
        },
        parent_trace_id=session_id,
        decision_id_hint=session_id,
    )


def _resource_updated_fragment(
    entry: dict[str, Any],
    session: dict[str, Any],
    opts: McpIngestOptions,
) -> Fragment | None:
    params = dict(entry["frame"].get("params") or {})
    resource = str(params.get("uri") or params.get("resource") or "unknown_resource")
    counters = session.setdefault("resource_mutations", {})
    count = int(counters.get(resource, 0))
    if count >= opts.max_state_mutations_per_resource:
        return None
    counters[resource] = count + 1
    session_id = entry["session_id"]
    return _fragment(
        f"mcp_{session_id}_resource_updated_{count + 1}",
        FragmentKind.STATE_MUTATION,
        timestamp=float(entry["ts"]),
        actor_id=_server_actor(session, opts, session_id),
        payload={
            "resource": _uri_value(resource, opts.store_uris),
            "event": "resource updated",
            "state_change_magnitude": 1.0,
        },
        parent_trace_id=session_id,
        decision_id_hint=session_id,
    )
