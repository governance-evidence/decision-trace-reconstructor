"""OTLP span normalization public facade."""

from __future__ import annotations

from typing import Any

from .record_normalize import normalise_span_record
from .time_ids import to_unix_seconds
from .value_normalize import _parse_otlp_attributes


def normalise_otlp_input(data: Any) -> list[dict[str, Any]]:
    """Normalise supported OTLP input shapes to flattened SpanRecord dicts."""
    if isinstance(data, list):
        return [normalise_span_record(item) for item in data]
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported OTLP input payload: {type(data)!r}")

    if "resourceSpans" in data:
        if not isinstance(data["resourceSpans"], list):
            raise ValueError("Unsupported OTLP payload: resourceSpans must be a list")
        return _flatten_export_trace_request(data)
    if "spans" in data and isinstance(data["spans"], list):
        return [normalise_span_record(item) for item in data["spans"]]
    if _looks_like_span_record(data):
        return [normalise_span_record(data)]
    raise ValueError("Unsupported OTLP payload: expected resourceSpans, spans, or span record")


def _flatten_export_trace_request(data: dict[str, Any]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for resource_spans in data.get("resourceSpans", []):
        resource = _parse_otlp_attributes(
            (resource_spans.get("resource") or {}).get("attributes", [])
        )
        for scope_spans in resource_spans.get("scopeSpans", []):
            scope = scope_spans.get("scope") or {}
            scope_info = {
                "name": scope.get("name"),
                "version": scope.get("version"),
            }
            for span in scope_spans.get("spans", []):
                spans.append(
                    normalise_span_record(
                        {
                            **span,
                            "resource": resource,
                            "scope": scope_info,
                        }
                    )
                )
    return spans


def _looks_like_span_record(data: dict[str, Any]) -> bool:
    return any(
        key in data
        for key in (
            "trace_id",
            "traceId",
            "span_id",
            "spanId",
            "start_time_unix_nano",
            "startTimeUnixNano",
        )
    )


__all__ = [
    "normalise_otlp_input",
    "normalise_span_record",
    "to_unix_seconds",
]
