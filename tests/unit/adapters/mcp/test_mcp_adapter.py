"""MCP adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reconstructor.adapters.mcp import (
    McpIngestOptions,
    find_claude_desktop_logs,
    load_transcript_file,
    transcript_to_fragments,
    transcript_to_manifest,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _entry(
    *,
    ts: float,
    session_id: str,
    direction: str,
    frame: dict[str, Any],
    transport: str = "stdio",
) -> dict[str, Any]:
    return {
        "ts": ts,
        "dir": direction,
        "transport": transport,
        "session_id": session_id,
        "frame": frame,
    }


def _base_transcript() -> list[dict[str, Any]]:
    return [
        _entry(
            ts=1735689600.0,
            session_id="session-a",
            direction="client_to_server",
            frame={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "host-a"}},
            },
        ),
        _entry(
            ts=1735689600.1,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True},
                    },
                    "serverInfo": {"name": "filesystem", "version": "1.0.0"},
                },
            },
        ),
        _entry(
            ts=1735689600.2,
            session_id="session-a",
            direction="client_to_server",
            frame={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ),
        _entry(
            ts=1735689600.3,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"tools": [{"name": "read_file"}, {"name": "write_file"}]},
            },
        ),
        _entry(
            ts=1735689600.4,
            session_id="session-a",
            direction="client_to_server",
            frame={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/read",
                "params": {"uri": "file:///tmp/report.txt"},
            },
        ),
        _entry(
            ts=1735689600.5,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 3,
                "result": {"contents": [{"uri": "file:///tmp/report.txt", "text": "report body"}]},
            },
        ),
        _entry(
            ts=1735689600.6,
            session_id="session-a",
            direction="client_to_server",
            frame={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "prompts/get",
                "params": {"name": "summarize", "arguments": {"topic": "refund"}},
            },
        ),
        _entry(
            ts=1735689600.7,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 4,
                "result": {
                    "description": "Summarize",
                    "messages": [{"role": "user", "content": "Summarize refund"}],
                },
            },
        ),
        _entry(
            ts=1735689600.8,
            session_id="session-a",
            direction="client_to_server",
            frame={
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "write_file",
                    "arguments": {"path": "/tmp/out.txt", "text": "hello"},
                },
            },
        ),
        _entry(
            ts=1735689600.9,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 5,
                "result": {"content": [{"type": "text", "text": "ok"}]},
            },
        ),
        _entry(
            ts=1735689601.0,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 6,
                "method": "sampling/createMessage",
                "params": {
                    "messages": [{"role": "user", "content": "Summarize"}],
                    "systemPrompt": "Be terse.",
                },
            },
        ),
        _entry(
            ts=1735689601.1,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": "file:///tmp/out.txt"},
            },
        ),
        _entry(
            ts=1735689601.2,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "method": "notifications/progress",
                "params": {"progress": 50},
            },
        ),
    ]


def test_initialize_response_produces_config_snapshot() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )

    assert config.payload["server_name"] == "filesystem"
    assert config.actor_id == "filesystem"
    assert config.stack_tier is StackTier.CROSS_STACK


def test_tools_list_emits_config_snapshot_only_with_opt_in() -> None:
    fragments = transcript_to_fragments(_base_transcript(), McpIngestOptions(emit_tools_list=True))
    assert any(fragment.fragment_id.endswith("tools_list") for fragment in fragments)

    fragments_without = transcript_to_fragments(_base_transcript())
    assert not any(fragment.fragment_id.endswith("tools_list") for fragment in fragments_without)


def test_resources_read_maps_to_retrieval_result() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    retrieval = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.RETRIEVAL_RESULT
    )

    assert retrieval.payload["retrieved"] == [
        {"uri": "file:///tmp/report.txt", "text": "report body"}
    ]
    assert set(retrieval.payload["query"]) == {"sha256", "length"}


def test_prompts_get_maps_to_agent_message() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    prompt = next(fragment for fragment in fragments if fragment.fragment_id.endswith("prompt_get"))
    assert prompt.kind is FragmentKind.AGENT_MESSAGE
    assert prompt.payload["prompt_name"] == "summarize"


def test_sampling_create_message_maps_to_partial_model_generation() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    sampling = next(fragment for fragment in fragments if fragment.fragment_id.endswith("sampling"))
    assert sampling.kind is FragmentKind.MODEL_GENERATION
    assert sampling.payload["partial"] is True
    assert sampling.actor_id == "filesystem"


def test_tools_call_maps_to_tool_call() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    tool = next(fragment for fragment in fragments if fragment.fragment_id.endswith("tool_call"))

    assert tool.kind is FragmentKind.TOOL_CALL
    assert tool.payload["tool_name"] == "write_file"
    assert tool.payload["args"]["path"] == "/tmp/out.txt"
    assert tool.payload["result"] == {"content": [{"type": "text", "text": "ok"}]}


def test_tools_call_error_emits_error_fragment() -> None:
    transcript = _base_transcript()
    transcript[9] = _entry(
        ts=1735689600.9,
        session_id="session-a",
        direction="server_to_client",
        frame={"jsonrpc": "2.0", "id": 5, "result": {"isError": True, "content": "failed"}},
    )
    fragments = transcript_to_fragments(transcript)
    error = next(fragment for fragment in fragments if fragment.kind is FragmentKind.ERROR)
    assert error.payload["error"] == {"isError": True, "content": "failed"}


def test_state_mutation_tool_regex_pairs_tool_call() -> None:
    fragments = transcript_to_fragments(
        _base_transcript(), McpIngestOptions(state_mutation_tool_pattern=r"write_.*")
    )
    assert any(fragment.fragment_id.endswith("tool_state") for fragment in fragments)


def test_notifications_resources_updated_maps_to_state_mutation() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    state = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("resource_updated_1")
    )
    assert state.kind is FragmentKind.STATE_MUTATION
    assert state.actor_id == "filesystem"


def test_state_mutation_rate_limiting_applies_per_resource() -> None:
    transcript = _base_transcript() + [
        _entry(
            ts=1735689601.15 + index,
            session_id="session-a",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": "file:///tmp/out.txt"},
            },
        )
        for index in range(3)
    ]
    fragments = transcript_to_fragments(
        transcript, McpIngestOptions(max_state_mutations_per_resource=2)
    )
    states = [
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.STATE_MUTATION
        and "resource_updated" in fragment.fragment_id
    ]
    assert len(states) == 2


def test_skip_rules_drop_operational_methods() -> None:
    fragments = transcript_to_fragments(_base_transcript())
    assert not any("progress" in fragment.fragment_id for fragment in fragments)


def test_multi_session_filtering_keeps_one_session() -> None:
    transcript = _base_transcript() + [
        _entry(
            ts=1735689602.0,
            session_id="session-b",
            direction="client_to_server",
            frame={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        ),
        _entry(
            ts=1735689602.1,
            session_id="session-b",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"serverInfo": {"name": "git", "version": "1.0.0"}},
            },
        ),
    ]
    fragments = transcript_to_fragments(transcript, McpIngestOptions(session_id="session-b"))
    assert all(fragment.parent_trace_id == "session-b" for fragment in fragments)


def test_per_session_server_name_attribution() -> None:
    transcript = _base_transcript() + [
        _entry(
            ts=1735689602.0,
            session_id="session-b",
            direction="client_to_server",
            frame={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        ),
        _entry(
            ts=1735689602.1,
            session_id="session-b",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"serverInfo": {"name": "git", "version": "1.0.0"}},
            },
        ),
        _entry(
            ts=1735689602.2,
            session_id="session-b",
            direction="server_to_client",
            frame={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "sampling/createMessage",
                "params": {"messages": []},
            },
        ),
    ]
    fragments = transcript_to_fragments(transcript)
    git_sampling = next(
        fragment
        for fragment in fragments
        if fragment.parent_trace_id == "session-b"
        and fragment.kind is FragmentKind.MODEL_GENERATION
    )
    assert git_sampling.actor_id == "git"


def test_all_mcp_fragments_are_cross_stack() -> None:
    fragments = transcript_to_fragments(
        _base_transcript(),
        McpIngestOptions(emit_tools_list=True, state_mutation_tool_pattern=r"write_.*"),
    )
    assert all(fragment.stack_tier is StackTier.CROSS_STACK for fragment in fragments)


def test_store_uris_preserves_resource_uri() -> None:
    fragments = transcript_to_fragments(_base_transcript(), McpIngestOptions(store_uris=True))
    retrieval = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.RETRIEVAL_RESULT
    )
    assert retrieval.payload["query"] == "file:///tmp/report.txt"


def test_manifest_round_trip_reconstructs_fragments() -> None:
    manifest = transcript_to_manifest(_base_transcript(), scenario_id="mcp_round_trip")
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]

    assert manifest["stack_tier"] == "cross_stack"
    assert fragments[0].parent_trace_id == "session-a"


def test_json_rpc_malformed_line_tolerance(tmp_path: Path) -> None:
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps(_base_transcript()[0]),
        json.dumps(_base_transcript()[1]) + ",",
        '{"ts": 1735689600.2, "dir": "client_to_server",',
    ]
    path.write_text("\n".join(lines) + "\n")

    frames = load_transcript_file(path)

    assert len(frames) == 2


def test_auth_fields_are_redacted_during_parse(tmp_path: Path) -> None:
    path = tmp_path / "transcript.jsonl"
    payload = _entry(
        ts=1735689600.0,
        session_id="session-a",
        direction="client_to_server",
        frame={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"Authorization": "Bearer secret-token", "api_key": "secret"},
        },
    )
    path.write_text(json.dumps(payload) + "\n")

    frames = load_transcript_file(path)
    params = frames[0]["frame"]["params"]
    assert params["Authorization"] == "[REDACTED]"
    assert params["api_key"] == "[REDACTED]"


def test_find_claude_desktop_logs_returns_paths(tmp_path: Path, monkeypatch: Any) -> None:
    logs_dir = tmp_path / "Library" / "Logs" / "Claude"
    logs_dir.mkdir(parents=True)
    log_path = logs_dir / "mcp-server-demo.log"
    log_path.write_text("")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    matches = find_claude_desktop_logs()

    assert matches == [log_path]
