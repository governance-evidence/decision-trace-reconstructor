"""Shared Bedrock memory helpers."""

from __future__ import annotations

from typing import Any


def _memory_summaries(memory_contents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in memory_contents:
        if not isinstance(item, dict):
            continue
        summary = item.get("sessionSummary") or item.get("session_summary")
        if isinstance(summary, dict) and summary:
            summaries.append(summary)
    return summaries
