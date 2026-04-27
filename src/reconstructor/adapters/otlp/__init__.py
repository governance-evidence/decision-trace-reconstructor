"""OpenTelemetry GenAI OTLP trace adapter.

The adapter accepts either:

1. Canonical OTLP/JSON payloads shaped like ``ExportTraceServiceRequest``.
2. JSON arrays of flattened span dicts.
3. JSONL files where each line is either a flattened span dict or a
   canonical OTLP/JSON document fragment.

The public mapping API is deliberately offline-first and dict-driven so the
same logic can power fixtures, exported traces, and future network helpers.
"""

from __future__ import annotations

from .common import OtlpIngestOptions
from .loaders import load_spans_file, load_spans_protobuf, load_spans_url
from .normalize import normalise_otlp_input
from .pipeline import spans_to_fragments, spans_to_manifest

__all__ = [
    "OtlpIngestOptions",
    "load_spans_file",
    "load_spans_protobuf",
    "load_spans_url",
    "normalise_otlp_input",
    "spans_to_fragments",
    "spans_to_manifest",
]
