"""CLI-level tests for ``decision-trace ingest otlp``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from reconstructor.cli import main


def _span_payload() -> list[dict[str, Any]]:
    return [
        {
            "trace_id": "trace-cli-001",
            "span_id": "span-cli-001",
            "parent_span_id": None,
            "name": "chat gpt-4o-mini",
            "kind": "client",
            "start_time_unix_nano": 1735689600000000000,
            "end_time_unix_nano": 1735689601000000000,
            "attributes": {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "gpt-4o-mini",
                "gen_ai.agent.id": "cli_agent",
                "service.name": "agent-api",
            },
            "events": [],
            "status": {"code": "OK", "message": None},
            "resource": {"deployment.environment": "test"},
            "scope": {"name": "otel.test", "version": "1.0.0"},
        }
    ]


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

    return bytes(message.SerializeToString())


def test_cli_ingest_otlp_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "spans.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_span_payload()) + "\n")

    exit_code = main(
        [
            "ingest",
            "otlp",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "cli_otlp_file",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_otlp_file"
    assert manifest["fragments"][0]["kind"] == "model_generation"


def test_cli_ingest_otlp_from_protobuf_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "trace.pb"
    out_path = tmp_path / "fragments.json"
    input_path.write_bytes(_protobuf_trace_request_bytes())

    exit_code = main(
        [
            "ingest",
            "otlp",
            "--from-otel-protobuf",
            str(input_path),
            "--scenario-id",
            "cli_otlp_protobuf",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_otlp_protobuf"
    assert manifest["fragments"][0]["kind"] == "model_generation"


def test_cli_ingest_otlp_from_collector_writes_manifest(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_path = tmp_path / "fragments.json"

    def _fake_load_spans_url(url: str, *, timeout: float = 30.0) -> list[dict[str, Any]]:
        assert url == "http://collector.local/v1/traces"
        assert timeout == 7.5
        return _span_payload()

    monkeypatch.setattr("reconstructor.adapters.otlp.load_spans_url", _fake_load_spans_url)

    exit_code = main(
        [
            "ingest",
            "otlp",
            "--from-otlp-collector",
            "http://collector.local/v1/traces",
            "--collector-timeout",
            "7.5",
            "--scenario-id",
            "cli_otlp_collector",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_otlp_collector"
    assert manifest["fragments"][0]["actor_id"] == "cli_agent"


def test_cli_ingest_otlp_requires_exactly_one_input_mode(tmp_path: Path) -> None:
    out_path = tmp_path / "fragments.json"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "ingest",
                "otlp",
                "--scenario-id",
                "cli_otlp_missing_input",
                "--out",
                str(out_path),
            ]
        )

    assert exc_info.value.code == 2


def test_cli_ingest_otlp_rejects_conflicting_input_modes(tmp_path: Path) -> None:
    input_path = tmp_path / "spans.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_span_payload()) + "\n")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "ingest",
                "otlp",
                "--from-file",
                str(input_path),
                "--from-otlp-collector",
                "http://collector.local/v1/traces",
                "--scenario-id",
                "cli_otlp_conflict",
                "--out",
                str(out_path),
            ]
        )

    assert exc_info.value.code == 2


def test_cli_ingest_otlp_rejects_invalid_json(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "spans.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("{not-json\n")

    exit_code = main(
        [
            "ingest",
            "otlp",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "cli_otlp_bad_json",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error:" in captured.err
    assert not out_path.exists()


def test_cli_ingest_otlp_rejects_malformed_resource_spans_payload(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "spans.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps({"resourceSpans": None}) + "\n")

    exit_code = main(
        [
            "ingest",
            "otlp",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "cli_otlp_bad_resource_spans",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "resourceSpans must be a list" in captured.err
    assert not out_path.exists()
