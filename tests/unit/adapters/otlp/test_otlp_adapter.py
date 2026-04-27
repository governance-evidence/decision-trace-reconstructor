"""OpenTelemetry GenAI adapter mapping tests."""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
from pathlib import Path
from typing import Any

import pytest

from reconstructor.adapters.otlp import (
    OtlpIngestOptions,
    load_spans_protobuf,
    load_spans_url,
    normalise_otlp_input,
    spans_to_fragments,
    spans_to_manifest,
)
from reconstructor.core.fragment import FragmentKind, StackTier


def _span(
    span_id: str,
    operation: str | None,
    *,
    name: str = "span",
    start: int = 1_735_689_600_000_000_000,
    attrs: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    status: dict[str, Any] | None = None,
    kind: str = "client",
    parent_span_id: str | None = None,
    resource: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_attrs = {
        "gen_ai.system": "openai",
        "service.name": "agent-api",
    }
    if operation is not None:
        base_attrs["gen_ai.operation.name"] = operation
    if attrs:
        base_attrs.update(attrs)
    return {
        "trace_id": "trace-001",
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "kind": kind,
        "start_time_unix_nano": start,
        "end_time_unix_nano": start + 1_000_000,
        "attributes": base_attrs,
        "events": events or [],
        "status": status or {"code": "OK", "message": None},
        "resource": resource or {"deployment.environment": "prod"},
        "scope": {"name": "otel.test", "version": "1.0.0"},
    }


def _event(
    name: str,
    *,
    content: str | None = None,
    ts: int | None = None,
    attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(attrs or {})
    if content is not None:
        payload.setdefault("content", content)
    return {
        "name": name,
        "time_unix_nano": ts or 1_735_689_600_000_000_500,
        "attributes": payload,
    }


def _protobuf_trace_request_bytes() -> bytes:
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    message = ExportTraceServiceRequest()
    resource_spans = message.resource_spans.add()
    resource_attr = resource_spans.resource.attributes.add()
    resource_attr.key = "service.name"
    resource_attr.value.string_value = "agent-api"

    scope_spans = resource_spans.scope_spans.add()
    scope_spans.scope.name = "opentelemetry.instrumentation.openai"
    scope_spans.scope.version = "0.1.0"
    span = scope_spans.spans.add()
    span.trace_id = bytes.fromhex("00" * 15 + "01")
    span.span_id = bytes.fromhex("00" * 7 + "01")
    span.name = "chat gpt-4o"
    span.kind = 3
    span.start_time_unix_nano = 1735689600000000000
    span.end_time_unix_nano = 1735689601000000000

    attr_system = span.attributes.add()
    attr_system.key = "gen_ai.system"
    attr_system.value.string_value = "openai"
    attr_operation = span.attributes.add()
    attr_operation.key = "gen_ai.operation.name"
    attr_operation.value.string_value = "chat"

    return message.SerializeToString()


def test_chat_span_maps_to_model_generation() -> None:
    fragments = spans_to_fragments(
        [
            _span(
                "s1",
                "chat",
                name="chat gpt-4o",
                attrs={
                    "gen_ai.request.model": "gpt-4o",
                    "gen_ai.usage.input_tokens": 10,
                    "gen_ai.usage.output_tokens": 4,
                },
            )
        ]
    )
    assert len(fragments) == 1
    assert fragments[0].kind is FragmentKind.MODEL_GENERATION
    assert fragments[0].payload["model_id"] == "gpt-4o"
    assert fragments[0].payload["token_count"] == 14
    assert fragments[0].payload["internal_reasoning"] == "opaque"


def test_execute_tool_emits_tool_call_and_state_mutation_when_pattern_matches() -> None:
    fragments = spans_to_fragments(
        [
            _span(
                "s1",
                "execute_tool",
                name="db_exec",
                attrs={
                    "gen_ai.tool.name": "db_exec",
                    "gen_ai.tool.call.arguments": {"sql": "DROP TABLE users"},
                },
            )
        ],
        OtlpIngestOptions(state_mutation_tool_pattern=r"(drop|exec|delete)"),
    )
    assert len(fragments) == 2
    assert fragments[0].kind is FragmentKind.TOOL_CALL
    assert fragments[1].kind is FragmentKind.STATE_MUTATION
    assert fragments[1].timestamp > fragments[0].timestamp


def test_embeddings_span_is_skipped() -> None:
    assert spans_to_fragments([_span("s1", "embeddings")]) == []


def test_create_agent_maps_to_config_snapshot() -> None:
    fragments = spans_to_fragments(
        [_span("s1", "create_agent", attrs={"gen_ai.agent.id": "agent-alpha"})]
    )
    assert len(fragments) == 1
    assert fragments[0].kind is FragmentKind.CONFIG_SNAPSHOT
    assert fragments[0].payload["config_version"] == "agent-alpha"


def test_invoke_agent_maps_to_agent_message() -> None:
    fragments = spans_to_fragments([_span("s1", "invoke_agent", name="handoff to reviewer")])
    assert len(fragments) == 1
    assert fragments[0].kind is FragmentKind.AGENT_MESSAGE


def test_user_and_system_events_emit_agent_message_fragments() -> None:
    fragments = spans_to_fragments(
        [
            _span(
                "s1",
                "chat",
                events=[
                    _event("gen_ai.user.message", content="hello", attrs={"role": "user"}),
                    _event("gen_ai.system.message", content="be precise", attrs={"role": "system"}),
                    _event(
                        "gen_ai.assistant.message", content="world", attrs={"role": "assistant"}
                    ),
                ],
            )
        ]
    )
    assert [fragment.kind for fragment in fragments].count(FragmentKind.AGENT_MESSAGE) == 2
    assert [fragment.kind for fragment in fragments].count(FragmentKind.MODEL_GENERATION) == 1


def test_error_status_emits_paired_error_fragment() -> None:
    fragments = spans_to_fragments(
        [_span("s1", "chat", status={"code": "ERROR", "message": "rate limit"})]
    )
    assert len(fragments) == 2
    assert fragments[1].kind is FragmentKind.ERROR
    assert fragments[1].payload["error"] == "rate limit"


def test_legacy_llm_prefix_is_accepted_in_lenient_mode() -> None:
    fragments = spans_to_fragments(
        [
            _span(
                "s1",
                None,
                attrs={
                    "llm.operation.name": "chat",
                    "llm.request.model": "gpt-4o-mini",
                },
            )
        ]
    )
    assert len(fragments) == 1
    assert fragments[0].kind is FragmentKind.MODEL_GENERATION
    assert fragments[0].payload["model_id"] == "gpt-4o-mini"


def test_sampling_guard_refuses_low_sample_rate_by_default() -> None:
    with pytest.raises(ValueError, match="sampled"):
        spans_to_fragments([_span("s1", "chat", attrs={"otel.trace.sample_rate": 0.1})])


def test_sampling_guard_can_be_overridden() -> None:
    fragments = spans_to_fragments(
        [_span("s1", "chat", attrs={"otel.trace.sample_rate": 0.1})],
        OtlpIngestOptions(accept_sampled=True),
    )
    assert len(fragments) == 1


def test_cross_stack_elevation_uses_server_address_outside_mesh() -> None:
    fragments = spans_to_fragments(
        [
            _span(
                "s1",
                "execute_tool",
                attrs={
                    "gen_ai.tool.name": "search_web",
                    "server.address": "api.tavily.com",
                },
            )
        ],
        OtlpIngestOptions(within_stack_services=("agent-api", "internal-rag")),
    )
    assert fragments[0].stack_tier is StackTier.CROSS_STACK


def test_actor_override_pins_actor_id() -> None:
    fragments = spans_to_fragments(
        [_span("s1", "chat", attrs={"gen_ai.agent.id": "specialist"})],
        OtlpIngestOptions(actor_override="primary_agent"),
    )
    assert fragments[0].actor_id == "primary_agent"


def test_auto_architecture_promotes_multi_agent_when_multiple_agent_ids_exist() -> None:
    manifest = spans_to_manifest(
        [
            _span("s1", "chat", attrs={"gen_ai.agent.id": "planner"}),
            _span(
                "s2",
                "invoke_agent",
                attrs={"gen_ai.agent.id": "reviewer"},
                start=1_735_689_600_100_000_000,
            ),
        ],
        scenario_id="otlp_demo",
        opts=OtlpIngestOptions(auto_architecture=True),
    )
    assert manifest["architecture"] == "multi_agent"


def test_normalise_otlp_export_trace_request_shape() -> None:
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "agent-api"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "opentelemetry.instrumentation.openai",
                            "version": "0.1.0",
                        },
                        "spans": [
                            {
                                "traceId": "TRACE-001",
                                "spanId": "SPAN-001",
                                "name": "chat gpt-4o",
                                "kind": "SPAN_KIND_CLIENT",
                                "startTimeUnixNano": "1735689600000000000",
                                "endTimeUnixNano": "1735689601000000000",
                                "attributes": [
                                    {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                                    {
                                        "key": "gen_ai.operation.name",
                                        "value": {"stringValue": "chat"},
                                    },
                                ],
                                "events": [],
                                "status": {"code": "STATUS_CODE_OK"},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    spans = normalise_otlp_input(payload)
    assert len(spans) == 1
    assert spans[0]["trace_id"] == "trace-001"
    assert spans[0]["span_id"] == "span-001"
    assert spans[0]["kind"] == "client"
    assert spans[0]["resource"]["service.name"] == "agent-api"


def test_load_spans_protobuf_reads_export_trace_service_request(tmp_path: Path) -> None:
    path = tmp_path / "trace.pb"
    path.write_bytes(_protobuf_trace_request_bytes())

    spans = load_spans_protobuf(path)
    assert len(spans) == 1
    assert spans[0]["trace_id"].endswith("01")
    assert spans[0]["span_id"].endswith("01")
    assert spans[0]["attributes"]["gen_ai.operation.name"] == "chat"


def test_load_spans_url_reads_otlp_json_response() -> None:
    payload = json.dumps(
        [
            _span(
                "s1",
                "chat",
                attrs={"gen_ai.request.model": "gpt-4o-mini"},
            )
        ]
    ).encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{httpd.server_address[1]}/v1/traces"
            spans = load_spans_url(url)
        finally:
            httpd.shutdown()
            thread.join()

    assert len(spans) == 1
    assert spans[0]["attributes"]["gen_ai.request.model"] == "gpt-4o-mini"


def test_load_spans_url_reads_otlp_protobuf_response() -> None:
    payload = _protobuf_trace_request_bytes()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{httpd.server_address[1]}/v1/traces"
            spans = load_spans_url(url)
        finally:
            httpd.shutdown()
            thread.join()

    assert len(spans) == 1
    assert spans[0]["trace_id"].endswith("01")
    assert spans[0]["attributes"]["gen_ai.operation.name"] == "chat"
