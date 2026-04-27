"""Microsoft Agent Framework / AutoGen v0.4 offline adapter."""

from __future__ import annotations

from .common import AgentFrameworkIngestOptions
from .events import load_events_file, normalise_agentframework_input
from .pipeline import events_to_fragments, events_to_manifest

__all__ = [
    "AgentFrameworkIngestOptions",
    "events_to_fragments",
    "events_to_manifest",
    "load_events_file",
    "normalise_agentframework_input",
]
