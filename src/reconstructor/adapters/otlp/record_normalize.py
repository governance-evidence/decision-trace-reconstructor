"""Normalization for flattened OTLP span and event records."""

from __future__ import annotations

from typing import Any

from .time_ids import _norm_parent_id, _norm_trace_like_id, _to_unix_nano
from .value_normalize import (
    _normalise_span_kind,
    _normalise_status,
    _parse_otlp_attributes,
    _translate_legacy_attributes,
)


def normalise_span_record(span: dict[str, Any] | Any) -> dict[str, Any]:
    """Normalize one flattened span-like object to the internal SpanRecord shape."""
    if not isinstance(span, dict):
        raise TypeError(f"Unsupported span object: {type(span)!r}")

    attributes = span.get("attributes") or {}
    if isinstance(attributes, list):
        attributes = _parse_otlp_attributes(attributes)
    else:
        attributes = dict(attributes)
    attributes = _translate_legacy_attributes(attributes)

    resource = span.get("resource") or {}
    if isinstance(resource, dict) and "attributes" in resource:
        resource = _parse_otlp_attributes(resource.get("attributes", []))
    else:
        resource = dict(resource)

    scope = span.get("scope") or {}
    events = [_normalise_event(event, span) for event in span.get("events", [])]

    start_nano = _to_unix_nano(span.get("start_time_unix_nano", span.get("startTimeUnixNano")))
    end_nano = _to_unix_nano(span.get("end_time_unix_nano", span.get("endTimeUnixNano")))

    return {
        "trace_id": _norm_trace_like_id(
            span.get("trace_id", span.get("traceId")), expected_bytes=16
        ),
        "span_id": _norm_trace_like_id(span.get("span_id", span.get("spanId")), expected_bytes=8),
        "parent_span_id": _norm_parent_id(span.get("parent_span_id", span.get("parentSpanId"))),
        "name": str(span.get("name") or "unnamed_span"),
        "kind": _normalise_span_kind(span.get("kind")),
        "start_time_unix_nano": start_nano,
        "end_time_unix_nano": end_nano or start_nano,
        "attributes": attributes,
        "events": events,
        "status": _normalise_status(span.get("status")),
        "resource": resource,
        "scope": {
            "name": scope.get("name"),
            "version": scope.get("version"),
        },
    }


def _normalise_event(event: Any, parent_span: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise TypeError(f"Unsupported OTLP event: {type(event)!r}")
    attributes = event.get("attributes") or {}
    if isinstance(attributes, list):
        attributes = _parse_otlp_attributes(attributes)
    else:
        attributes = dict(attributes)
    attributes = _translate_legacy_attributes(attributes)

    raw_time = event.get("time_unix_nano", event.get("timeUnixNano"))
    inferred = raw_time in (None, "")
    ts_nano = _to_unix_nano(raw_time)
    if not ts_nano:
        ts_nano = _to_unix_nano(
            parent_span.get("start_time_unix_nano", parent_span.get("startTimeUnixNano"))
        )
    if inferred:
        attributes = {**attributes, "timestamp_inferred": True}
    return {
        "name": str(event.get("name") or ""),
        "time_unix_nano": ts_nano,
        "attributes": attributes,
    }
