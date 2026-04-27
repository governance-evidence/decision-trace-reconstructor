"""CLI-level tests for ``decision-trace ingest crewai``."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main


def _events() -> list[dict[str, object]]:
    return [
        {
            "event_type": "crew_kickoff_started",
            "timestamp": 1735752000.0,
            "payload": {
                "crew_name": "Editorial Crew",
                "agents": [{"role": "Researcher"}, {"role": "Writer"}],
                "tasks": [{"id": "task-1", "description": "Research"}],
                "process": "hierarchical",
            },
        },
        {
            "event_type": "task_started",
            "timestamp": 1735752000.1,
            "payload": {
                "crew_name": "Editorial Crew",
                "task_id": "task-1",
                "task_description": "Research",
                "assigned_agent": "Researcher",
            },
        },
        {
            "event_type": "tool_usage_started",
            "timestamp": 1735752000.2,
            "payload": {
                "crew_name": "Editorial Crew",
                "agent_role": "Researcher",
                "tool_name": "web_search",
                "args": {"query": "CrewAI"},
            },
        },
        {
            "event_type": "tool_usage_finished",
            "timestamp": 1735752000.3,
            "payload": {
                "crew_name": "Editorial Crew",
                "agent_role": "Researcher",
                "tool_name": "web_search",
                "output": "done",
            },
        },
    ]


def test_cli_ingest_crewai_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_events()) + "\n")

    exit_code = main(
        [
            "ingest",
            "crewai",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "crewai_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "crewai_cli"
    assert manifest["architecture"] == "multi_agent"


def test_cli_ingest_crewai_auto_architecture(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    events = [
        {
            "event_type": "crew_kickoff_started",
            "timestamp": 1735752000.0,
            "payload": {
                "crew_name": "Solo Crew",
                "agents": [{"role": "Solo"}],
                "tasks": [{"id": "task-1", "description": "Write"}],
                "process": "sequential",
            },
        },
        {
            "event_type": "task_started",
            "timestamp": 1735752000.1,
            "payload": {"crew_name": "Solo Crew", "task_id": "task-1", "assigned_agent": "Solo"},
        },
    ]
    input_path.write_text(json.dumps(events) + "\n")

    exit_code = main(
        [
            "ingest",
            "crewai",
            "--from-file",
            str(input_path),
            "--auto-architecture",
            "--scenario-id",
            "crewai_auto",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["architecture"] == "single_agent"


def test_cli_ingest_crewai_filters_crew_name(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    events = _events() + [
        {
            "event_type": "task_started",
            "timestamp": 1735752001.0,
            "payload": {"crew_name": "Other Crew", "task_id": "task-z", "assigned_agent": "Other"},
        }
    ]
    input_path.write_text(json.dumps(events) + "\n")

    exit_code = main(
        [
            "ingest",
            "crewai",
            "--from-file",
            str(input_path),
            "--crew-name",
            "Editorial Crew",
            "--scenario-id",
            "crewai_filter",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert all(
        fragment["parent_trace_id"] == "Editorial Crew" for fragment in manifest["fragments"]
    )


def test_cli_ingest_crewai_no_config_snapshot(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_events()) + "\n")

    exit_code = main(
        [
            "ingest",
            "crewai",
            "--from-file",
            str(input_path),
            "--no-emit-config-snapshot",
            "--scenario-id",
            "crewai_no_cfg",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert not any(fragment["kind"] == "config_snapshot" for fragment in manifest["fragments"])


def test_cli_ingest_crewai_rejects_empty_input(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("[]\n")

    exit_code = main(
        [
            "ingest",
            "crewai",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "crewai_empty",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "CrewAI telemetry input is empty" in captured.err
    assert not out_path.exists()


def test_cli_ingest_crewai_rejects_invalid_json(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("{not-json\n")

    exit_code = main(
        [
            "ingest",
            "crewai",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "crewai_bad_json",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error:" in captured.err
    assert not out_path.exists()
