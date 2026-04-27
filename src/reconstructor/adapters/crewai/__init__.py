"""CrewAI telemetry offline adapter."""

from __future__ import annotations

from .common import CrewAIIngestOptions
from .events import load_events_file, normalise_crewai_input
from .pipeline import events_to_fragments, events_to_manifest

__all__ = [
    "CrewAIIngestOptions",
    "events_to_fragments",
    "events_to_manifest",
    "load_events_file",
    "normalise_crewai_input",
]
