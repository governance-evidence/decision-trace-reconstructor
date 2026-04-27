"""Bedrock session-to-manifest conversion pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...core.fragment import Fragment
from ...core.manifest import manifest_dict
from .common import BedrockIngestOptions
from .fragments import _session_to_fragments
from .normalize import normalise_session as _normalise_session


def sessions_to_fragments(
    sessions: Iterable[dict[str, Any] | Any],
    opts: BedrockIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or BedrockIngestOptions()
    normalised = [_normalise_session(session) for session in sessions]
    normalised.sort(key=lambda session: (session["_ts"], session["session_id"]))

    out: list[Fragment] = []
    for session in normalised:
        out.extend(_session_to_fragments(session, cfg))
    out.sort(key=lambda fragment: (fragment.timestamp, fragment.fragment_id))
    return out


def sessions_to_manifest(
    sessions: Iterable[dict[str, Any] | Any],
    scenario_id: str,
    opts: BedrockIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or BedrockIngestOptions()
    normalised = [_normalise_session(session) for session in sessions]
    fragments = sessions_to_fragments(normalised, cfg)
    architecture = _infer_architecture(normalised, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )


def _infer_architecture(sessions: list[dict[str, Any]], opts: BedrockIngestOptions) -> str:
    if not opts.auto_architecture:
        return opts.architecture
    for session in sessions:
        for event in session.get("events", []):
            block = event.get("block") or {}
            collaborator = block.get("agentCollaboratorInvocationInput")
            if collaborator:
                return "multi_agent"
    return opts.architecture
