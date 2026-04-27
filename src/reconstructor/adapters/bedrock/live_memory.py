"""Memory attachment helpers for Bedrock live ingest."""

from __future__ import annotations

from typing import Any


def _attach_memory_contents(
    sessions: list[dict[str, Any]],
    memory_id: str,
    memory_contents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    attached: list[dict[str, Any]] = []
    for session in sessions:
        updated = dict(session)
        updated["memory_id"] = memory_id
        updated["memory_contents"] = list(memory_contents)
        attached.append(updated)
    return attached
