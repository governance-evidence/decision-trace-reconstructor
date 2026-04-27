"""CLI-level tests for ``decision-trace ingest openai-agents``."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main


def _trace_payload(trace_id: str, group_id: str = "conversation-1") -> dict[str, object]:
    return {
        "trace_id": trace_id,
        "workflow_name": "customer_support_workflow",
        "group_id": group_id,
        "spans": [
            {
                "span_id": "span-agent",
                "trace_id": trace_id,
                "parent_id": None,
                "started_at": "2025-04-15T09:00:00Z",
                "ended_at": "2025-04-15T09:00:01Z",
                "span_data": {"type": "agent", "name": "triage_agent"},
                "error": None,
            },
            {
                "span_id": "span-handoff",
                "trace_id": trace_id,
                "parent_id": "span-agent",
                "started_at": "2025-04-15T09:00:01Z",
                "ended_at": "2025-04-15T09:00:01.100000Z",
                "span_data": {"type": "handoff", "handoff_to": "billing_agent"},
                "error": None,
            },
        ],
    }


def test_cli_ingest_openai_agents_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "trace.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_trace_payload("trace_cli_1")) + "\n")

    exit_code = main(
        [
            "ingest",
            "openai-agents",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "openai_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "openai_cli"
    assert manifest["fragments"][0]["kind"] == "agent_message"


def test_cli_ingest_openai_agents_auto_architecture(tmp_path: Path) -> None:
    input_path = tmp_path / "trace.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_trace_payload("trace_cli_2")) + "\n")

    exit_code = main(
        [
            "ingest",
            "openai-agents",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "openai_cli_multi",
            "--auto-architecture",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["architecture"] == "multi_agent"


def test_cli_ingest_openai_agents_group_into_scenarios(tmp_path: Path) -> None:
    input_path = tmp_path / "traces.json"
    out_dir = tmp_path / "out"
    input_path.write_text(
        json.dumps(
            [
                _trace_payload("trace_cli_3", group_id="group-1"),
                _trace_payload("trace_cli_4", group_id="group-1"),
            ]
        )
        + "\n"
    )

    exit_code = main(
        [
            "ingest",
            "openai-agents",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "openai_grouped",
            "--group-into-scenarios",
            "--out",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    outputs = sorted(out_dir.glob("*.json"))
    assert [path.name for path in outputs] == ["openai_grouped_1.json"]


def test_cli_ingest_openai_agents_rejects_stdout_for_multiple_manifests(tmp_path: Path) -> None:
    input_path = tmp_path / "traces.jsonl"
    input_path.write_text(
        "\n".join(
            json.dumps(item)
            for item in [_trace_payload("trace_cli_5"), _trace_payload("trace_cli_6")]
        )
        + "\n"
    )

    exit_code = main(
        [
            "ingest",
            "openai-agents",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "openai_multi",
            "--out",
            "-",
        ]
    )

    assert exit_code == 2
