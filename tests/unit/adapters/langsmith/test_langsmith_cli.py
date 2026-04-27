"""CLI-level tests for ``decision-trace ingest langsmith``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reconstructor.cli import main


def _run(run_id: str = "run-1", run_type: str = "tool") -> dict[str, object]:
    return {
        "id": run_id,
        "name": "write_report",
        "run_type": run_type,
        "start_time": "2025-01-01T00:00:00Z",
        "end_time": "2025-01-01T00:00:01Z",
        "inputs": {"path": "report.md"},
        "outputs": {},
        "error": None,
        "tags": [],
        "extra": {"metadata": {}},
        "events": [],
        "trace_id": "trace-001",
        "parent_run_id": None,
        "session_id": None,
        "status": "success",
    }


def test_cli_ingest_langsmith_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps({"runs": [_run()]}))

    exit_code = main(
        [
            "ingest",
            "langsmith",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "langsmith_cli",
            "--state-mutation-tools",
            "write_.*",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "langsmith_cli"
    assert [fragment["kind"] for fragment in manifest["fragments"]] == [
        "tool_call",
        "state_mutation",
    ]


def test_cli_ingest_langsmith_rejects_invalid_stack_tier(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps([_run()]))

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "ingest",
                "langsmith",
                "--from-file",
                str(input_path),
                "--stack-tier",
                "bad_tier",
                "--out",
                str(out_path),
            ]
        )

    assert exc_info.value.code == 2
    assert not out_path.exists()


def test_cli_ingest_langsmith_rejects_non_list_file_payload(tmp_path: Path) -> None:
    input_path = tmp_path / "runs.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps({"not_runs": []}))

    exit_code = main(
        [
            "ingest",
            "langsmith",
            "--from-file",
            str(input_path),
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 2
    assert not out_path.exists()
