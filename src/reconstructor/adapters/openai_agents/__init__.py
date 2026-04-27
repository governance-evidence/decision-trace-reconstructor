"""OpenAI Agents SDK trace adapter.

The shipped slice is offline-first and accepts exported trace JSON / JSONL
captured from the OpenAI Agents SDK tracing processors or dashboard export.
"""

from __future__ import annotations

from .common import OpenAIAgentsIngestOptions
from .events import load_traces_file, normalise_openai_agents_input
from .pipeline import trace_to_fragments, trace_to_manifest, traces_to_manifests

__all__ = [
    "OpenAIAgentsIngestOptions",
    "load_traces_file",
    "normalise_openai_agents_input",
    "trace_to_fragments",
    "trace_to_manifest",
    "traces_to_manifests",
]
