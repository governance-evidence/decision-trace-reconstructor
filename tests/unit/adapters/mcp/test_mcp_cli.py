"""CLI-level tests for ``decision-trace ingest mcp``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reconstructor.cli import main


def _transcript() -> list[dict[str, object]]:
    return [
        {
            "ts": 1735689600.0,
            "dir": "client_to_server",
            "transport": "stdio",
            "session_id": "session-a",
            "frame": {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        },
        {
            "ts": 1735689600.1,
            "dir": "server_to_client",
            "transport": "stdio",
            "session_id": "session-a",
            "frame": {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"serverInfo": {"name": "filesystem", "version": "1.0.0"}},
            },
        },
        {
            "ts": 1735689600.2,
            "dir": "client_to_server",
            "transport": "stdio",
            "session_id": "session-a",
            "frame": {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "write_file", "arguments": {"path": "/tmp/x"}},
            },
        },
        {
            "ts": 1735689600.3,
            "dir": "server_to_client",
            "transport": "stdio",
            "session_id": "session-a",
            "frame": {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": [{"type": "text", "text": "ok"}]},
            },
        },
    ]


def test_cli_ingest_mcp_from_file_writes_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "transcript.json"
    out_path = tmp_path / "fragments.json"
    input_path.write_text(json.dumps(_transcript()) + "\n")

    exit_code = main(
        [
            "ingest",
            "mcp",
            "--from-file",
            str(input_path),
            "--scenario-id",
            "mcp_cli",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "mcp_cli"
    assert manifest["stack_tier"] == "cross_stack"


def test_cli_ingest_mcp_emit_tools_list(tmp_path: Path) -> None:
    input_path = tmp_path / "transcript.json"
    out_path = tmp_path / "fragments.json"
    transcript = _transcript()
    transcript.extend(
        [
            {
                "ts": 1735689600.4,
                "dir": "client_to_server",
                "transport": "stdio",
                "session_id": "session-a",
                "frame": {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            },
            {
                "ts": 1735689600.5,
                "dir": "server_to_client",
                "transport": "stdio",
                "session_id": "session-a",
                "frame": {"jsonrpc": "2.0", "id": 3, "result": {"tools": [{"name": "write_file"}]}},
            },
        ]
    )
    input_path.write_text(json.dumps(transcript) + "\n")

    exit_code = main(
        [
            "ingest",
            "mcp",
            "--from-file",
            str(input_path),
            "--emit-tools-list",
            "--scenario-id",
            "mcp_cli_tools",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert any(fragment["fragment_id"].endswith("tools_list") for fragment in manifest["fragments"])


def test_cli_ingest_mcp_filters_session_id(tmp_path: Path) -> None:
    input_path = tmp_path / "transcript.json"
    out_path = tmp_path / "fragments.json"
    transcript = _transcript() + [
        {
            "ts": 1735689601.0,
            "dir": "client_to_server",
            "transport": "stdio",
            "session_id": "session-b",
            "frame": {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        },
        {
            "ts": 1735689601.1,
            "dir": "server_to_client",
            "transport": "stdio",
            "session_id": "session-b",
            "frame": {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"serverInfo": {"name": "git", "version": "1.0.0"}},
            },
        },
    ]
    input_path.write_text(json.dumps(transcript) + "\n")

    exit_code = main(
        [
            "ingest",
            "mcp",
            "--from-file",
            str(input_path),
            "--session-id",
            "session-b",
            "--scenario-id",
            "mcp_cli_filter",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert all(fragment["parent_trace_id"] == "session-b" for fragment in manifest["fragments"])


def test_cli_ingest_mcp_from_claude_desktop(tmp_path: Path, monkeypatch: Any) -> None:
    log_path = tmp_path / "mcp-server-demo.log"
    log_path.write_text(json.dumps(_transcript()) + "\n")

    monkeypatch.setattr("reconstructor.adapters.mcp.find_claude_desktop_logs", lambda: [log_path])

    out_path = tmp_path / "fragments.json"
    exit_code = main(
        [
            "ingest",
            "mcp",
            "--from-claude-desktop",
            "--scenario-id",
            "mcp_cli_logs",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(out_path.read_text())
    assert manifest["scenario_id"] == "mcp_cli_logs"
