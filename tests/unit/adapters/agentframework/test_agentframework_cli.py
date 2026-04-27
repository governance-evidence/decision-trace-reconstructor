"""CLI-level tests for ``decision-trace ingest agentframework``."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main


def _events() -> list[dict[str, object]]:
    return [
        {
            "ts": 1735689600.0,
            "event_type": "speaker_selected",
            "message_id": "speaker-1",
            "trace_id": "trace-1",
            "sender": "system",
            "payload": {"selected": "planner", "candidates": ["planner", "executor"]},
        },
        {
            "ts": 1735689600.01,
            "event_type": "message_published",
            "message_id": "pub-1",
            "trace_id": "trace-1",
            "topic": "research_topic",
            "sender": "planner",
            "recipient": "executor",
            "payload": {"content": "Find docs", "topic": "research_topic"},
        },
        {
            "ts": 1735689600.02,
            "event_type": "tool_called",
            "message_id": "tool-1",
            "trace_id": "trace-1",
            "sender": "executor",
            "payload": {
                "agent_id": "executor",
                "tool_name": "web_search",
                "args": {"query": "autogen"},
            },
        },
        {
            "ts": 1735689600.03,
            "event_type": "tool_returned",
            "message_id": "tool-1-return",
            "trace_id": "trace-1",
            "sender": "executor",
            "payload": {"agent_id": "executor", "tool_name": "web_search", "result": "done"},
        },
    ]


def test_cli_ingest_agentframework_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_events()) + "\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "af_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "af_cli"


def test_cli_ingest_agentframework_auto_architecture(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_events()) + "\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--auto-architecture",
            "--scenario-id",
            "af_auto",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["architecture"] == "multi_agent"


def test_cli_ingest_agentframework_topic_filter(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    events = _events() + [
        {
            "ts": 1735689600.04,
            "event_type": "message_published",
            "message_id": "pub-2",
            "trace_id": "trace-1",
            "topic": "other",
            "sender": "planner",
            "payload": {"content": "ignore", "topic": "other"},
        }
    ]
    input_path.write_text(json.dumps(events) + "\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--topic-filter",
            "research_.*",
            "--scenario-id",
            "af_topic",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert (
        sum(
            1 for fragment in manifest["fragments"] if fragment["fragment_id"].endswith("published")
        )
        == 1
    )


def test_cli_ingest_agentframework_runtime_override(tmp_path: Path) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_events()) + "\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--runtime",
            "grpc",
            "--scenario-id",
            "af_grpc",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    published = next(
        fragment
        for fragment in manifest["fragments"]
        if fragment["fragment_id"].endswith("published")
    )
    assert published["stack_tier"] == "cross_stack"


def test_cli_ingest_agentframework_rejects_empty_input(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("[]\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "af_empty",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Agent Framework input is empty" in captured.err
    assert not out_path.exists()


def test_cli_ingest_agentframework_rejects_invalid_json(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "events.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("{not-json\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "af_bad_json",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error:" in captured.err
    assert not out_path.exists()


def test_cli_ingest_agentframework_writes_manifest_to_stdout(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps(_events()) + "\n")

    exit_code = main(
        [
            "ingest",
            "agentframework",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "af_stdout",
            "--out",
            "-",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    manifest = json.loads(captured.out)
    assert manifest["scenario_id"] == "af_stdout"
    assert "wrote" not in captured.out
