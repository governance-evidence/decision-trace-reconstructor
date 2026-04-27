"""CLI-level tests for ``decision-trace ingest anthropic``."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main


def _round(round_id: str, timestamp: float, *, command: str = "ls -la") -> dict[str, object]:
    return {
        "request": {
            "model": "claude-3-5-sonnet-20241022",
            "system": "You are support agent.",
            "messages": [{"role": "user", "content": "Need help"}],
            "metadata": {"user_id": "support_agent"},
        },
        "response": {
            "id": f"msg_{round_id}",
            "type": "message",
            "role": "assistant",
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 12, "output_tokens": 8},
            "content": [
                {"type": "thinking", "thinking": "private reasoning"},
                {
                    "type": "tool_use",
                    "id": f"tool_{round_id}",
                    "name": "bash",
                    "input": {"command": command},
                },
            ],
        },
        "timestamp": timestamp,
    }


def test_cli_ingest_anthropic_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "history.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps([_round("0001", 1735689600.0)]) + "\n")

    exit_code = main(
        [
            "ingest",
            "anthropic",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "anthropic_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "anthropic_cli"
    assert manifest["fragments"][0]["kind"] in {"config_snapshot", "policy_snapshot"}


def test_cli_ingest_anthropic_store_thinking(tmp_path: Path) -> None:
    input_path = tmp_path / "history.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps([_round("0001", 1735689600.0)]) + "\n")

    exit_code = main(
        [
            "ingest",
            "anthropic",
            "--from-file",
            str(input_path),
            "--store-thinking",
            "--scenario-id",
            "anthropic_cli_thinking",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    thinking = next(
        fragment
        for fragment in manifest["fragments"]
        if fragment["fragment_id"].endswith("thinking_1")
    )
    assert thinking["payload"]["thinking"] == "private reasoning"


def test_cli_ingest_anthropic_bash_readonly_pattern(tmp_path: Path) -> None:
    input_path = tmp_path / "history.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps([_round("0001", 1735689600.0, command="echo hi")]) + "\n")

    exit_code = main(
        [
            "ingest",
            "anthropic",
            "--from-file",
            str(input_path),
            "--bash-readonly-pattern",
            "^(echo)\\b",
            "--scenario-id",
            "anthropic_cli_bash",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert not any(fragment["kind"] == "state_mutation" for fragment in manifest["fragments"])


def test_cli_ingest_anthropic_rejects_empty_file(tmp_path: Path) -> None:
    input_path = tmp_path / "empty.jsonl"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("")

    exit_code = main(
        [
            "ingest",
            "anthropic",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "anthropic_empty",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 2
