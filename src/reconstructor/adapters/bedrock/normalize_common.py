"""Shared constants and scalar coercion for Bedrock normalization."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_TRACE_TYPES = (
    "preProcessingTrace",
    "orchestrationTrace",
    "knowledgeBaseLookupTrace",
    "postProcessingTrace",
    "guardrailTrace",
    "returnControl",
    "failureTrace",
)
_SESSION_METADATA_KEYS = (
    "agent_id",
    "agent_alias_id",
    "agent_version",
    "foundation_model",
    "memory_id",
    "memory_contents",
    "memory_summary",
)


def _to_epoch_seconds(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            return numeric / 1000.0
        return numeric
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0.0
        if stripped.isdigit():
            numeric = float(stripped)
            if numeric > 10_000_000_000:
                return numeric / 1000.0
            return numeric
        return datetime.fromisoformat(stripped.replace("Z", "+00:00")).timestamp()
    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")
