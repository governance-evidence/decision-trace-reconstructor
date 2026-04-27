"""CLI-level tests for ``decision-trace ingest pydantic-ai``."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main


def _runs() -> list[dict[str, object]]:
    return [
        {
            "run_id": "run-1",
            "agent_name": "Assistant",
            "model": "openai:gpt-4o",
            "deps_type": "SupportDeps",
            "result_type": "SupportResult",
            "result_schema": {"type": "object"},
            "messages": [
                {
                    "kind": "request",
                    "timestamp": 1777291200.0,
                    "parts": [
                        {
                            "part_kind": "system-prompt",
                            "content": "Follow policy",
                            "timestamp": 1777291200.0,
                        },
                        {
                            "part_kind": "user-prompt",
                            "content": "Help me",
                            "timestamp": 1777291201.0,
                        },
                    ],
                },
                {
                    "kind": "response",
                    "model_name": "openai:gpt-4o",
                    "timestamp": 1777291202.0,
                    "parts": [
                        {"part_kind": "text", "content": "Answer", "timestamp": 1777291202.0},
                    ],
                },
            ],
            "result": {"answer": "Answer"},
            "usage": {"requests": 1},
            "ts_start": 1777291200.0,
            "ts_end": 1777291203.0,
        }
    ]


def test_cli_ingest_pydantic_ai_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_runs()) + "\n")

    exit_code = main(
        [
            "ingest",
            "pydantic-ai",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "pa_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "pa_cli"


def test_cli_ingest_pydantic_ai_auto_architecture(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    runs = _runs() + [{**_runs()[0], "run_id": "run-2", "agent_name": "Reviewer"}]
    input_path.write_text(json.dumps(runs) + "\n")

    exit_code = main(
        [
            "ingest",
            "pydantic-ai",
            "--from-file",
            str(input_path),
            "--auto-architecture",
            "--scenario-id",
            "pa_auto",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["architecture"] == "multi_agent"


def test_cli_ingest_pydantic_ai_emits_system_prompt_when_requested(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_runs()) + "\n")

    exit_code = main(
        [
            "ingest",
            "pydantic-ai",
            "--from-file",
            str(input_path),
            "--emit-system-prompt",
            "--scenario-id",
            "pa_sys",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert any("system" in fragment["fragment_id"] for fragment in manifest["fragments"])


def test_cli_ingest_pydantic_ai_takeover_mapping(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    runs = [
        {
            "run_id": "run-1",
            "agent_name": "Assistant",
            "model": "openai:gpt-4o",
            "deps_type": "SupportDeps",
            "result_type": "SupportResult",
            "result_schema": {"type": "object"},
            "tools": [{"tool_name": "request_human", "is_takeover": True}],
            "messages": [
                {
                    "kind": "response",
                    "timestamp": 1777291202.0,
                    "parts": [
                        {
                            "part_kind": "tool-call",
                            "tool_name": "request_human",
                            "tool_call_id": "call-1",
                            "args": {},
                            "timestamp": 1777291202.0,
                        }
                    ],
                },
                {
                    "kind": "request",
                    "timestamp": 1777291203.0,
                    "parts": [
                        {
                            "part_kind": "tool-return",
                            "tool_name": "request_human",
                            "tool_call_id": "call-1",
                            "content": "APPROVED",
                            "timestamp": 1777291203.0,
                        }
                    ],
                },
            ],
            "result": {"answer": "ok"},
            "usage": {},
            "ts_start": 1777291200.0,
            "ts_end": 1777291204.0,
        }
    ]
    input_path.write_text(json.dumps(runs) + "\n")

    exit_code = main(
        [
            "ingest",
            "pydantic-ai",
            "--from-file",
            str(input_path),
            "--takeover-tool-pattern",
            "request_.*",
            "--human-approval-pattern",
            "APPROVED",
            "--scenario-id",
            "pa_takeover",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert any(fragment["kind"] == "human_approval" for fragment in manifest["fragments"])


def test_cli_ingest_pydantic_ai_rejects_empty_input(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("[]\n")

    exit_code = main(
        [
            "ingest",
            "pydantic-ai",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "pa_empty",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Pydantic AI input is empty" in captured.err
    assert not out_path.exists()


def test_cli_ingest_pydantic_ai_rejects_invalid_json(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("{not-json\n")

    exit_code = main(
        [
            "ingest",
            "pydantic-ai",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "pa_bad_json",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error:" in captured.err
    assert not out_path.exists()
