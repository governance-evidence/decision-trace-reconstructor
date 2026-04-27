"""Edge-case contracts for OTLP normalization and ingest."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any

import pytest

from reconstructor.adapters.otlp import OtlpIngestOptions, normalise_otlp_input, spans_to_fragments
from reconstructor.adapters.otlp.record_normalize import normalise_span_record
from reconstructor.adapters.otlp.time_ids import (
    _norm_parent_id,
    _norm_trace_like_id,
    to_unix_seconds,
)
from reconstructor.adapters.otlp.value_normalize import (
    _normalise_span_kind,
    _normalise_status,
    _otlp_value_to_python,
    _parse_otlp_attributes,
)
from reconstructor.core.fragment import FragmentKind, StackTier


def _span(
    span_id: str = "s1",
    operation: str | None = "chat",
    *,
    start: int = 1_735_689_600_000_000_000,
    attrs: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    parent_span_id: str | None = None,
) -> dict[str, Any]:
    attributes = {"service.name": "agent-api"}
    if operation is not None:
        attributes["gen_ai.operation.name"] = operation
    if attrs:
        attributes.update(attrs)
    return {
        "trace_id": "trace-001",
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": operation or "span",
        "kind": "client",
        "start_time_unix_nano": start,
        "end_time_unix_nano": start + 1_000_000,
        "attributes": attributes,
        "events": events or [],
        "status": {"code": "OK", "message": None},
        "resource": {},
        "scope": {},
    }


def test_otlp_attribute_values_cover_scalar_array_kvlist_and_malformed_items() -> None:
    attrs = _parse_otlp_attributes(
        [
            {"key": "string", "value": {"stringValue": "hello"}},
            {"key": "int", "value": {"intValue": "42"}},
            {"key": "double", "value": {"doubleValue": "3.5"}},
            {"key": "bool", "value": {"boolValue": True}},
            {
                "key": "array",
                "value": {
                    "arrayValue": {
                        "values": [
                            {"stringValue": "a"},
                            {"intValue": "2"},
                        ]
                    }
                },
            },
            {
                "key": "kv",
                "value": {
                    "kvlistValue": {"values": [{"key": "nested", "value": {"stringValue": "yes"}}]}
                },
            },
            {"value": {"stringValue": "ignored"}},
            "not-a-dict",  # type: ignore[list-item]
        ]
    )

    assert attrs == {
        "string": "hello",
        "int": 42,
        "double": 3.5,
        "bool": True,
        "array": ["a", 2],
        "kv": {"nested": "yes"},
    }
    assert _otlp_value_to_python({"arrayValue": "bad"}) == []
    assert _otlp_value_to_python({"kvlistValue": "bad"}) == {}
    assert _otlp_value_to_python({"unknown": "kept"}) == {"unknown": "kept"}


def test_status_and_span_kind_normalization_accept_wire_variants() -> None:
    assert _normalise_status(None) == {"code": "OK", "message": None}
    assert _normalise_status("STATUS_CODE_ERROR") == {"code": "ERROR", "message": None}
    assert _normalise_status(123) == {"code": "OK", "message": None}
    assert _normalise_status({"code": "STATUS_CODE_ERROR", "message": "boom"}) == {
        "code": "ERROR",
        "message": "boom",
    }

    assert _normalise_span_kind(None) == "internal"
    assert _normalise_span_kind(3) == "client"
    assert _normalise_span_kind(99) == "internal"
    assert _normalise_span_kind("SPAN_KIND_SERVER") == "server"
    assert _normalise_span_kind("custom_kind") == "custom_kind"


def test_timestamp_and_trace_id_normalization_cover_wire_variants() -> None:
    assert to_unix_seconds(None) == 0.0
    assert to_unix_seconds(True) == 1e-9
    assert to_unix_seconds(1_735_689_600_000_000_000) == 1_735_689_600.0
    assert to_unix_seconds(1_735_689_600.0) == 1_735_689_600.0
    assert to_unix_seconds("1735689600000000000") == 1_735_689_600.0
    assert to_unix_seconds(datetime(2025, 1, 1, tzinfo=UTC)) == 1_735_689_600.0
    assert to_unix_seconds("2025-01-01T00:00:00Z") == 1_735_689_600.0

    trace_bytes = bytes.fromhex("00" * 15 + "01")
    span_bytes = bytes.fromhex("00" * 7 + "02")
    assert _norm_trace_like_id(base64.b64encode(trace_bytes).decode(), expected_bytes=16).endswith(
        "01"
    )
    assert _norm_parent_id(base64.b64encode(span_bytes).decode()).endswith("02")
    assert _norm_parent_id("") is None
    assert _norm_trace_like_id("NOT_BASE64", expected_bytes=8) == "not_base64"

    with pytest.raises(TypeError, match="Unsupported timestamp type"):
        to_unix_seconds(object())


def test_normalise_otlp_input_rejects_unsupported_payload_shapes() -> None:
    with pytest.raises(TypeError, match="Unsupported OTLP input payload"):
        normalise_otlp_input("bad")
    with pytest.raises(ValueError, match="Unsupported OTLP payload"):
        normalise_otlp_input({"resourceSpans": None})


def test_normalise_span_record_rejects_bad_span_and_event_objects() -> None:
    with pytest.raises(TypeError, match="Unsupported span object"):
        normalise_span_record("bad")
    with pytest.raises(TypeError, match="Unsupported OTLP event"):
        normalise_span_record(_span(events=["bad"]))


def test_normalise_span_record_infers_event_timestamp_from_parent_span() -> None:
    span = normalise_span_record(
        _span(
            events=[
                {
                    "name": "gen_ai.user.message",
                    "attributes": [{"key": "content", "value": {"stringValue": "hello"}}],
                }
            ]
        )
    )

    assert span["events"][0]["time_unix_nano"] == span["start_time_unix_nano"]
    assert span["events"][0]["attributes"]["timestamp_inferred"] is True


def test_normalise_otlp_input_accepts_single_span_and_spans_wrapper() -> None:
    single = normalise_otlp_input(_span())
    wrapped = normalise_otlp_input({"spans": [_span("s2")]})

    assert single[0]["span_id"] == "s1"
    assert wrapped[0]["span_id"] == "s2"


def test_sampling_rate_option_is_enforced_even_without_span_attribute() -> None:
    with pytest.raises(ValueError, match="sampled at rate 0.250"):
        spans_to_fragments([_span()], OtlpIngestOptions(sampling_rate=0.25))

    fragments = spans_to_fragments(
        [_span()],
        OtlpIngestOptions(sampling_rate=0.25, accept_sampled=True),
    )
    assert fragments[0].kind is FragmentKind.MODEL_GENERATION


def test_stack_tier_override_and_content_storage_are_respected() -> None:
    fragments = spans_to_fragments(
        [
            _span(
                attrs={
                    "demm.stack_tier": "cross_stack",
                    "gen_ai.request.model": "gpt-4o-mini",
                },
                events=[
                    {
                        "name": "gen_ai.assistant.message",
                        "time_unix_nano": 1_735_689_600_000_000_500,
                        "attributes": {"content": "stored content"},
                    }
                ],
            )
        ],
        OtlpIngestOptions(store_content=True),
    )

    assert fragments[0].stack_tier is StackTier.CROSS_STACK
    assert fragments[0].payload["assistant_messages"] == ["stored content"]


def test_spans_to_fragments_orders_by_timestamp_then_span_id() -> None:
    fragments = spans_to_fragments(
        [
            _span("b", "chat", start=1_735_689_600_000_000_000),
            _span("a", "chat", start=1_735_689_600_000_000_000),
            _span("c", "chat", start=1_735_689_599_000_000_000),
        ]
    )

    assert [fragment.fragment_id for fragment in fragments] == [
        "otlp_c_model",
        "otlp_a_model",
        "otlp_b_model",
    ]
