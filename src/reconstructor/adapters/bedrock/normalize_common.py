"""Shared constants and scalar coercion for Bedrock normalization."""

from __future__ import annotations

from typing import Any

from .._time import to_epoch_seconds

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
    return to_epoch_seconds(value, ms_heuristic=True)
