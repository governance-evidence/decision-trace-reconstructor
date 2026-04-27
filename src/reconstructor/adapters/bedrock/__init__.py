"""AWS Bedrock AgentCore trace adapter.

The public module keeps the stable adapter API while implementation details live
in focused modules for live fetches, normalisation, IO, and fragment mapping.
"""

from __future__ import annotations

from .common import BedrockIngestOptions
from .io import load_sessions_file, validate_sessions_complete
from .live import (
    fetch_agent_memory_contents,
    fetch_cloudwatch_events,
    load_sessions_cloudwatch,
)
from .normalize import normalise_bedrock_input
from .pipeline import sessions_to_fragments, sessions_to_manifest

__all__ = [
    "BedrockIngestOptions",
    "fetch_agent_memory_contents",
    "fetch_cloudwatch_events",
    "load_sessions_file",
    "load_sessions_cloudwatch",
    "normalise_bedrock_input",
    "sessions_to_fragments",
    "sessions_to_manifest",
    "validate_sessions_complete",
]
