"""Pydantic AI adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.adapters.pydantic_ai import (
    PydanticAIIngestOptions,
    load_runs_file,
    runs_to_fragments,
    runs_to_manifest,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _run(*, agent_name: str = "Assistant", run_id: str = "run-1") -> dict[str, object]:
    return {
        "run_id": run_id,
        "agent_name": agent_name,
        "model": "openai:gpt-4o",
        "deps_type": "SupportDeps",
        "result_type": "SupportResult",
        "result_schema": {"type": "object", "properties": {"answer": {"type": "string"}}},
        "tools": [
            {
                "tool_name": "search_docs",
                "description": "Search docs",
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "https://api.example.com"}
                    },
                },
                "is_takeover": False,
            },
            {
                "tool_name": "request_human",
                "description": "Escalate to human",
                "params_schema": {"type": "object"},
                "is_takeover": True,
            },
        ],
        "messages": [
            {
                "kind": "request",
                "timestamp": "2026-04-27T12:00:00Z",
                "parts": [
                    {
                        "part_kind": "system-prompt",
                        "content": "Follow policy",
                        "timestamp": "2026-04-27T12:00:00Z",
                    },
                    {
                        "part_kind": "user-prompt",
                        "content": "Help me",
                        "timestamp": "2026-04-27T12:00:01Z",
                    },
                ],
            },
            {
                "kind": "response",
                "model_name": "openai:gpt-4o",
                "timestamp": "2026-04-27T12:00:02Z",
                "parts": [
                    {
                        "part_kind": "thinking",
                        "content": "internal chain",
                        "timestamp": "2026-04-27T12:00:02Z",
                    },
                    {
                        "part_kind": "text",
                        "content": "Draft answer",
                        "timestamp": "2026-04-27T12:00:02.1Z",
                    },
                    {
                        "part_kind": "tool-call",
                        "tool_name": "search_docs",
                        "tool_call_id": "call-1",
                        "args": {"query": "policy"},
                        "timestamp": "2026-04-27T12:00:02.2Z",
                    },
                ],
            },
            {
                "kind": "request",
                "timestamp": "2026-04-27T12:00:03Z",
                "parts": [
                    {
                        "part_kind": "tool-return",
                        "tool_name": "search_docs",
                        "tool_call_id": "call-1",
                        "content": {"result": "policy snippet"},
                        "timestamp": "2026-04-27T12:00:03Z",
                    },
                    {
                        "part_kind": "retry-prompt",
                        "content": "Validation failed: answer missing required field",
                        "timestamp": "2026-04-27T12:00:03.1Z",
                    },
                ],
            },
            {
                "kind": "response",
                "model_name": "openai:gpt-4o",
                "timestamp": "2026-04-27T12:00:04Z",
                "parts": [
                    {
                        "part_kind": "text",
                        "content": "Final answer",
                        "timestamp": "2026-04-27T12:00:04Z",
                    },
                    {
                        "part_kind": "tool-call",
                        "tool_name": "request_human",
                        "tool_call_id": "call-2",
                        "args": {"reason": "approval"},
                        "timestamp": "2026-04-27T12:00:04.1Z",
                    },
                ],
            },
            {
                "kind": "request",
                "timestamp": "2026-04-27T12:00:05Z",
                "parts": [
                    {
                        "part_kind": "tool-return",
                        "tool_name": "request_human",
                        "tool_call_id": "call-2",
                        "content": "APPROVED by supervisor",
                        "timestamp": "2026-04-27T12:00:05Z",
                    },
                ],
            },
        ],
        "result": {"answer": "approved answer"},
        "usage": {"requests": 2, "request_tokens": 100, "response_tokens": 50},
        "ts_start": "2026-04-27T12:00:00Z",
        "ts_end": "2026-04-27T12:00:06Z",
    }


def test_run_record_emits_config_snapshot() -> None:
    fragments = runs_to_fragments([_run()])
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert config.payload["agent_name"] == "Assistant"


def test_result_schema_is_embedded_in_config_snapshot() -> None:
    fragments = runs_to_fragments([_run()])
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert config.payload["result_schema"]["type"] == "object"


def test_user_prompt_maps_to_agent_message() -> None:
    fragments = runs_to_fragments([_run()])
    user = next(fragment for fragment in fragments if fragment.fragment_id.endswith("user_2"))
    assert user.kind is FragmentKind.AGENT_MESSAGE
    assert user.payload["content"] == "Help me"


def test_system_prompt_is_ignored_by_default() -> None:
    fragments = runs_to_fragments([_run()])
    assert not any("system" in fragment.fragment_id for fragment in fragments)


def test_system_prompt_opt_in_emits_config_snapshot() -> None:
    fragments = runs_to_fragments([_run()], PydanticAIIngestOptions(emit_system_prompt=True))
    system_fragment = next(fragment for fragment in fragments if "system" in fragment.fragment_id)
    assert system_fragment.kind is FragmentKind.CONFIG_SNAPSHOT


def test_response_message_maps_to_model_generation() -> None:
    fragments = runs_to_fragments([_run()])
    models = [fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION]
    assert len(models) == 2


def test_thinking_blocks_are_redacted() -> None:
    fragments = runs_to_fragments([_run()])
    model = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION
    )
    assert model.payload["internal_reasoning"] == "opaque"
    assert "internal chain" not in str(model.payload)


def test_text_parts_are_absorbed_into_model_generation() -> None:
    fragments = runs_to_fragments([_run()])
    model = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION
    )
    assert model.payload["text"] == "Draft answer"


def test_tool_call_args_are_carried_through() -> None:
    fragments = runs_to_fragments([_run()])
    tool = next(
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.TOOL_CALL
        and fragment.payload["tool_name"] == "search_docs"
    )
    assert tool.payload["args"] == {"query": "policy"}


def test_tool_return_is_absorbed_into_tool_call_payload() -> None:
    fragments = runs_to_fragments([_run()])
    tool = next(
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.TOOL_CALL
        and fragment.payload["tool_name"] == "search_docs"
    )
    assert tool.payload["result"] == {"result": "policy snippet"}


def test_retry_prompt_emits_paired_error() -> None:
    fragments = runs_to_fragments([_run()])
    error = next(fragment for fragment in fragments if fragment.kind is FragmentKind.ERROR)
    assert "Validation failed" in error.payload["error"]
    assert error.payload["failed_fragment_kind"] == "tool_call"


def test_state_mutation_regex_emits_state_fragment() -> None:
    fragments = runs_to_fragments(
        [_run()], PydanticAIIngestOptions(state_mutation_tool_pattern=r"request_.*")
    )
    state = next(fragment for fragment in fragments if fragment.kind is FragmentKind.STATE_MUTATION)
    assert state.payload["tool_name"] == "request_human"


def test_cross_stack_tool_regex_elevates_tool_call() -> None:
    fragments = runs_to_fragments(
        [_run()], PydanticAIIngestOptions(cross_stack_tools_pattern=r"search_.*")
    )
    tool = next(
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.TOOL_CALL
        and fragment.payload["tool_name"] == "search_docs"
    )
    assert tool.stack_tier is StackTier.CROSS_STACK


def test_params_schema_url_elevates_tool_call() -> None:
    fragments = runs_to_fragments([_run()])
    tool = next(
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.TOOL_CALL
        and fragment.payload["tool_name"] == "search_docs"
    )
    assert tool.stack_tier is StackTier.CROSS_STACK


def test_takeover_tool_emits_human_approval() -> None:
    fragments = runs_to_fragments(
        [_run()],
        PydanticAIIngestOptions(
            takeover_tool_pattern=r"request_.*", human_approval_pattern=r"APPROVED"
        ),
    )
    approval = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.HUMAN_APPROVAL
    )
    assert approval.payload["tool_name"] == "request_human"


def test_takeover_tool_can_emit_human_rejection() -> None:
    run = _run()
    run["messages"][-1]["parts"][0]["content"] = "DENIED by supervisor"
    fragments = runs_to_fragments(
        [run],
        PydanticAIIngestOptions(
            takeover_tool_pattern=r"request_.*", human_approval_pattern=r"APPROVED"
        ),
    )
    rejection = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.HUMAN_REJECTION
    )
    assert rejection.payload["tool_name"] == "request_human"


def test_result_is_emitted_as_structured_agent_message() -> None:
    fragments = runs_to_fragments([_run()])
    result = next(fragment for fragment in fragments if fragment.fragment_id.endswith("result"))
    assert result.kind is FragmentKind.AGENT_MESSAGE
    assert result.payload["result"] == {"answer": "approved answer"}


def test_auto_architecture_detects_multi_agent() -> None:
    manifest = runs_to_manifest(
        [_run(agent_name="A", run_id="run-1"), _run(agent_name="B", run_id="run-2")],
        "pa_multi",
        PydanticAIIngestOptions(auto_architecture=True),
    )
    assert manifest["architecture"] == "multi_agent"


def test_auto_architecture_defaults_to_single_agent() -> None:
    manifest = runs_to_manifest(
        [_run()], "pa_single", PydanticAIIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "single_agent"


def test_actor_override_forces_run_actor() -> None:
    fragments = runs_to_fragments(
        [_run()], PydanticAIIngestOptions(actor_override="override_actor")
    )
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert config.actor_id == "override_actor"


def test_manifest_round_trip_reconstructs_fragments() -> None:
    manifest = runs_to_manifest([_run()], "pa_roundtrip")
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]
    assert manifest["stack_tier"] == "within_stack"
    assert fragments[0].parent_trace_id == "run-1"


def test_timestamp_parsing_accepts_iso8601() -> None:
    fragments = runs_to_fragments([_run()])
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert config.timestamp == 1777291200.0


def test_jsonl_loader_accepts_line_delimited_runs(tmp_path: Path) -> None:
    path = tmp_path / "runs.jsonl"
    path.write_text(
        "\n".join(json.dumps(run) for run in [_run(run_id="run-1"), _run(run_id="run-2")]) + "\n"
    )
    runs = load_runs_file(path)
    assert len(runs) == 2
