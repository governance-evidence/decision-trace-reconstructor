"""CLI-level tests for ``decision-trace ingest bedrock``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from reconstructor.cli import main


def _session_payload() -> dict[str, Any]:
    return {
        "sessionId": "bedrock-cli-001",
        "agentId": "agent-cli",
        "agentAliasId": "support-agent",
        "foundationModel": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "trace": {
            "orchestrationTrace": {
                "traceId": "trace-orch",
                "eventTime": "2025-01-01T00:00:02Z",
                "modelInvocationInput": {"prompt": "decide next step"},
                "modelInvocationOutput": {"text": "refund customer"},
                "invocationInput": {
                    "actionGroupInvocationInput": {
                        "actionGroupName": "orders_api",
                        "apiPath": "/refunds",
                        "verb": "POST",
                    }
                },
                "observation": {"finalResponse": {"text": "Refund queued"}},
            }
        },
    }


def test_cli_ingest_bedrock_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "bedrock.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps([_session_payload()]) + "\n")

    exit_code = main(
        [
            "ingest",
            "bedrock",
            "--from-file",
            str(input_path),
            "--cross-stack-action-groups",
            "orders_api",
            "--scenario-id",
            "cli_bedrock_file",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_bedrock_file"
    assert any(fragment["kind"] == "tool_call" for fragment in manifest["fragments"])
    assert any(fragment["stack_tier"] == "cross_stack" for fragment in manifest["fragments"])


def test_cli_ingest_bedrock_jsonl_cloudwatch_export(tmp_path: Path) -> None:
    input_path = tmp_path / "bedrock.jsonl"
    out_path = tmp_path / "fragments.json"
    cloudwatch = {
        "timestamp": 1735689600000,
        "message": json.dumps(_session_payload()),
    }
    input_path.write_text(json.dumps(cloudwatch) + "\n")

    exit_code = main(
        [
            "ingest",
            "bedrock",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "cli_bedrock_jsonl",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_bedrock_jsonl"
    assert manifest["fragments"][0]["kind"] == "config_snapshot"


def test_cli_ingest_bedrock_from_live_log_group_writes_manifest(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_path = tmp_path / "fragments.json"

    def _fake_load_sessions_cloudwatch(
        log_group_name: str,
        *,
        aws_profile: str | None = None,
        region: str | None = None,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
        memory_id: str | None = None,
    ) -> list[dict[str, Any]]:
        assert log_group_name == "/aws/bedrock/agent-runtime/demo"
        assert aws_profile == "sandbox"
        assert region == "us-east-1"
        assert start_time_ms == 1735689600000
        assert end_time_ms == 1735689700000
        assert session_id == "bedrock-cli-001"
        assert agent_id is None
        assert memory_id == "memory-user-001"
        return [_session_payload()]

    monkeypatch.setattr(
        "reconstructor.adapters.bedrock.load_sessions_cloudwatch",
        _fake_load_sessions_cloudwatch,
    )

    exit_code = main(
        [
            "ingest",
            "bedrock",
            "--log-group",
            "/aws/bedrock/agent-runtime/demo",
            "--aws-profile",
            "sandbox",
            "--region",
            "us-east-1",
            "--start-time-ms",
            "1735689600000",
            "--end-time-ms",
            "1735689700000",
            "--session-id",
            "bedrock-cli-001",
            "--memory-id",
            "memory-user-001",
            "--scenario-id",
            "cli_bedrock_live",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_bedrock_live"
    assert any(fragment["kind"] == "tool_call" for fragment in manifest["fragments"])


def test_cli_ingest_bedrock_rejects_conflicting_input_modes(tmp_path: Path) -> None:
    input_path = tmp_path / "bedrock.json"
    input_path.write_text(json.dumps([_session_payload()]) + "\n")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "ingest",
                "bedrock",
                "--from-file",
                str(input_path),
                "--log-group",
                "/aws/bedrock/agent-runtime/demo",
            ]
        )

    assert exc_info.value.code == 2


def test_cli_ingest_bedrock_rejects_partial_session_by_default(tmp_path: Path) -> None:
    input_path = tmp_path / "bedrock_partial.json"
    out_path = tmp_path / "fragments.json"
    partial = {
        "sessionId": "bedrock-partial-001",
        "agentId": "agent-cli",
        "agentAliasId": "support-agent",
        "trace": {
            "preProcessingTrace": {
                "traceId": "trace-pre",
                "eventTime": "2025-01-01T00:00:00Z",
                "modelInvocationInput": {"text": "truncated export"},
            }
        },
    }
    input_path.write_text(json.dumps([partial]) + "\n")

    exit_code = main(
        [
            "ingest",
            "bedrock",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "cli_bedrock_partial",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 2


def test_cli_ingest_bedrock_accepts_partial_session_with_override(tmp_path: Path) -> None:
    input_path = tmp_path / "bedrock_partial.json"
    out_path = tmp_path / "fragments.json"
    partial = {
        "sessionId": "bedrock-partial-001",
        "agentId": "agent-cli",
        "agentAliasId": "support-agent",
        "trace": {
            "preProcessingTrace": {
                "traceId": "trace-pre",
                "eventTime": "2025-01-01T00:00:00Z",
                "modelInvocationInput": {"text": "truncated export"},
            }
        },
    }
    input_path.write_text(json.dumps([partial]) + "\n")

    exit_code = main(
        [
            "ingest",
            "bedrock",
            "--from-file",
            str(input_path),
            "--accept-partial-sessions",
            "--scenario-id",
            "cli_bedrock_partial_ok",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "cli_bedrock_partial_ok"
