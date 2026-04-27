"""MCP transcript-to-manifest conversion pipeline."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, StackTier
from ...core.manifest import manifest_dict
from .common import _SKIPPED_METHODS, McpIngestOptions
from .events import _normalise_entry
from .fragments import (
    _resource_updated_fragment,
    _response_to_fragments,
    _sampling_fragment,
)


def transcript_to_fragments(
    frames: list[dict[str, Any]] | Any,
    opts: McpIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or McpIngestOptions()
    normalised = [
        _normalise_entry(frame, index)
        for index, frame in enumerate(frames if isinstance(frames, list) else [frames])
    ]
    if cfg.session_id is not None:
        normalised = [frame for frame in normalised if frame["session_id"] == cfg.session_id]
    normalised.sort(key=lambda item: (item["ts"], item["_index"]))

    session_state: dict[str, dict[str, Any]] = {}
    pending: dict[tuple[str, str], dict[str, Any]] = {}
    out: list[Fragment] = []
    for entry in normalised:
        session = session_state.setdefault(
            entry["session_id"], {"resource_mutations": {}, "server_name": None}
        )
        frame = entry["frame"]
        method = frame.get("method")

        if _is_response(frame):
            request = pending.pop((entry["session_id"], str(frame["id"])), None)
            if request is None:
                continue
            out.extend(_response_to_fragments(entry, request, session, cfg))
            continue

        if method in _SKIPPED_METHODS:
            continue

        if _is_request(frame):
            if method == "sampling/createMessage":
                out.append(_sampling_fragment(entry, session, cfg))
            elif method == "notifications/resources/updated":
                resource_fragment = _resource_updated_fragment(entry, session, cfg)
                if resource_fragment is not None:
                    out.append(resource_fragment)
            else:
                pending[(entry["session_id"], str(frame["id"]))] = entry
            continue

        if _is_notification(frame) and method == "notifications/resources/updated":
            resource_fragment = _resource_updated_fragment(entry, session, cfg)
            if resource_fragment is not None:
                out.append(resource_fragment)

    out.sort(key=lambda fragment: (fragment.timestamp, fragment.fragment_id))
    return out


def transcript_to_manifest(
    frames: list[dict[str, Any]] | Any,
    scenario_id: str,
    opts: McpIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or McpIngestOptions()
    fragments = transcript_to_fragments(frames, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=cfg.architecture,
        stack_tier=StackTier.CROSS_STACK,
        fragments=fragments,
    )


def _is_request(frame: dict[str, Any]) -> bool:
    return "method" in frame and "id" in frame


def _is_notification(frame: dict[str, Any]) -> bool:
    return "method" in frame and "id" not in frame


def _is_response(frame: dict[str, Any]) -> bool:
    return "id" in frame and "method" not in frame
