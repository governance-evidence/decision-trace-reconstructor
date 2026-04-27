"""Model Context Protocol transcript adapter."""

from __future__ import annotations

from .common import McpIngestOptions
from .events import (
    find_claude_desktop_logs as find_claude_desktop_logs,
)
from .events import (
    load_transcript_file,
    normalise_mcp_input,
)
from .pipeline import transcript_to_fragments, transcript_to_manifest

__all__ = [
    "McpIngestOptions",
    "load_transcript_file",
    "normalise_mcp_input",
    "transcript_to_fragments",
    "transcript_to_manifest",
]
