"""OTLP file, protobuf, and HTTP loaders."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from .normalize import normalise_otlp_input

_PROTOBUF_EXTRA_ERROR = (
    "OTLP protobuf ingest requires the [otlp] extra. Install with `pip install -e '.[otlp]'`."
)


def load_spans_file(path: str | Path) -> list[dict[str, Any]]:
    """Load OTLP spans from JSON / JSONL and normalise them into SpanRecord dicts."""
    raw = Path(path).read_text()
    return _load_spans_text(raw)


def load_spans_protobuf(path: str | Path) -> list[dict[str, Any]]:
    """Load OTLP spans from an ``ExportTraceServiceRequest`` protobuf file."""
    return _load_spans_protobuf_bytes(Path(path).read_bytes())


def load_spans_url(url: str, *, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch OTLP spans from an HTTP(S) endpoint returning JSON, JSONL, or protobuf."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/json,application/x-protobuf"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get_content_type().lower()

    if content_type in {"application/x-protobuf", "application/protobuf"}:
        return _load_spans_protobuf_bytes(body)

    text = body.decode("utf-8")
    return _load_spans_text(text)


def _load_spans_text(raw: str) -> list[dict[str, Any]]:
    raw = raw.strip()
    if not raw:
        return []
    if raw[0] in "[{":
        data = json.loads(raw)
        return normalise_otlp_input(data)

    spans: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        spans.extend(normalise_otlp_input(json.loads(line)))
    return spans


def _load_spans_protobuf_bytes(data: bytes) -> list[dict[str, Any]]:
    try:
        from google.protobuf.json_format import MessageToDict
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )
    except ImportError as exc:
        raise ImportError(_PROTOBUF_EXTRA_ERROR) from exc

    message = ExportTraceServiceRequest()
    message.ParseFromString(data)
    payload = MessageToDict(message, preserving_proto_field_name=False)
    return normalise_otlp_input(payload)


__all__ = [
    "load_spans_file",
    "load_spans_protobuf",
    "load_spans_url",
]
