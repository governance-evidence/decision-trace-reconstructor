"""Bedrock offline input loading and completeness validation."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .normalize import has_terminal_signal as _has_terminal_signal
from .normalize import normalise_bedrock_input
from .normalize import normalise_session as _normalise_session


def load_sessions_file(path: str | Path) -> list[dict[str, Any]]:
    """Load Bedrock sessions from JSON / JSONL offline exports."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_bedrock_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    items: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return normalise_bedrock_input(items)


def validate_sessions_complete(sessions: Iterable[dict[str, Any] | Any]) -> None:
    """Reject likely truncated Bedrock sessions unless the operator overrides.

    A session is considered complete when it contains at least one terminal
    signal: a final response, post-processing step, human return-control,
    failure trace, or an explicit persisted session summary.
    """
    incomplete: list[str] = []
    for raw in sessions:
        session = _normalise_session(raw)
        if not _has_terminal_signal(session):
            incomplete.append(session["session_id"])
    if incomplete:
        joined = ", ".join(sorted(incomplete))
        raise ValueError(
            "Bedrock export appears partial or truncated for session(s): "
            f"{joined}; pass accept_partial_sessions=True to override"
        )
