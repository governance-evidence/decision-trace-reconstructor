"""CLI-level tests for ``decision-trace ingest/validate generic-jsonl``."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from reconstructor.cli import main


def _mapping_yaml() -> str:
    return """
schema_version: "1.0"
source_name: cli_generic
fields:
  fragment_id: id
  timestamp: ts
  actor_id: actor
  payload: null
kind_field: kind
kind_map:
  prompt: agent_message
  tool: tool_call
skip_kinds: [heartbeat]
state_mutation_predicate:
  field: tool
  matches_regex: write_.*
absorb_followups:
  tool_result:
    absorbed_by_kind: tool
    payload_key: result
    pair_match_field: id
    parent_match_field: parent_id
stack_tier_default: within_stack
architecture: auto
""".strip()


def _records() -> list[dict[str, object]]:
    return [
        {"id": "e1", "ts": 1.0, "actor": "main", "kind": "prompt", "content": "hi"},
        {
            "id": "e2",
            "ts": 2.0,
            "actor": "main",
            "kind": "tool",
            "tool": "write_report",
            "args": {"path": "/tmp/out.md"},
        },
        {
            "id": "e3",
            "ts": 3.0,
            "actor": "main",
            "kind": "tool_result",
            "parent_id": "e2",
            "result": {"ok": True},
        },
    ]


def test_cli_ingest_generic_jsonl_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "agent_log.jsonl"
    mapping_path = tmp_path / "mapping.yaml"
    out_path = tmp_path / "fragments.json"
    input_path.write_text("\n".join(json.dumps(item) for item in _records()) + "\n")
    mapping_path.write_text(_mapping_yaml() + "\n")

    exit_code = main(
        [
            "ingest",
            "generic-jsonl",
            "--from-file",
            str(input_path),
            "--mapping",
            str(mapping_path),
            "--scenario-id",
            "generic_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "generic_cli"
    assert any(fragment["kind"] == "state_mutation" for fragment in manifest["fragments"])


def test_cli_ingest_generic_jsonl_from_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mapping_path = tmp_path / "mapping.yaml"
    out_path = tmp_path / "fragments.json"
    mapping_path.write_text(_mapping_yaml() + "\n")
    monkeypatch.setattr(
        "sys.stdin", io.StringIO("\n".join(json.dumps(item) for item in _records()) + "\n")
    )

    exit_code = main(
        [
            "ingest",
            "generic-jsonl",
            "--from-stdin",
            "--mapping",
            str(mapping_path),
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert len(manifest["fragments"]) == 3


def test_cli_ingest_generic_jsonl_strict_unknown_kind_fails(tmp_path: Path) -> None:
    input_path = tmp_path / "agent_log.jsonl"
    mapping_path = tmp_path / "mapping.yaml"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(
        json.dumps({"id": "e1", "ts": 1.0, "actor": "main", "kind": "mystery"}) + "\n"
    )
    mapping_path.write_text(_mapping_yaml() + "\n")

    exit_code = main(
        [
            "ingest",
            "generic-jsonl",
            "--from-file",
            str(input_path),
            "--mapping",
            str(mapping_path),
            "--strict-unknown-kinds",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 2
    assert not out_path.exists()


def test_cli_validate_generic_jsonl_reports_success(tmp_path: Path) -> None:
    input_path = tmp_path / "agent_log.jsonl"
    mapping_path = tmp_path / "mapping.yaml"
    input_path.write_text("\n".join(json.dumps(item) for item in _records()) + "\n")
    mapping_path.write_text(_mapping_yaml() + "\n")

    exit_code = main(
        [
            "validate",
            "generic-jsonl",
            "--mapping",
            str(mapping_path),
            "--sample-from",
            str(input_path),
        ]
    )

    assert exit_code == 0


def test_cli_validate_generic_jsonl_reports_issues(tmp_path: Path) -> None:
    input_path = tmp_path / "agent_log.jsonl"
    mapping_path = tmp_path / "mapping.yaml"
    input_path.write_text(json.dumps({"id": "e1", "kind": "prompt", "actor": "main"}) + "\n")
    mapping_path.write_text(_mapping_yaml() + "\n")

    exit_code = main(
        [
            "validate",
            "generic-jsonl",
            "--mapping",
            str(mapping_path),
            "--sample-from",
            str(input_path),
        ]
    )

    assert exit_code == 2
