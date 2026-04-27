"""Anthropic Messages / Computer Use adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reconstructor.adapters.anthropic import (
    AnthropicIngestOptions,
    load_rounds_file,
    rounds_to_fragments,
    rounds_to_manifest,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _tool_result_block(tool_use_id: str, content: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
    }


def _round(
    *,
    round_id: str,
    timestamp: float | str,
    messages: list[dict[str, Any]] | None = None,
    response_blocks: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    system: Any = "You are billing agent.",
    model: str = "claude-3-5-sonnet-20241022",
) -> dict[str, Any]:
    return {
        "round_id": round_id,
        "timestamp": timestamp,
        "request": {
            "model": model,
            "max_tokens": 1024,
            "system": system,
            "messages": messages or [{"role": "user", "content": "Need help with a refund"}],
            "tools": [
                {"name": "computer"},
                {"name": "bash"},
                {"name": "text_editor"},
                {"name": "search_web"},
            ],
            "metadata": metadata or {"user_id": "customer_support_operator"},
        },
        "response": {
            "id": f"msg_{round_id}",
            "type": "message",
            "role": "assistant",
            "model": model,
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 12, "output_tokens": 8},
            "content": response_blocks
            or [
                {"type": "thinking", "thinking": "private reasoning"},
                {"type": "text", "text": "I can help with that."},
            ],
        },
    }


def _tool_round(
    tool_name: str, tool_input: dict[str, Any], *, tool_use_id: str = "tool_1"
) -> list[dict[str, Any]]:
    return [
        _round(
            round_id="0001",
            timestamp=1735689600.0,
            response_blocks=[
                {"type": "text", "text": "Checking action."},
                {"type": "tool_use", "id": tool_use_id, "name": tool_name, "input": tool_input},
            ],
        ),
        _round(
            round_id="0002",
            timestamp=1735689601.0,
            messages=[
                {
                    "role": "user",
                    "content": [_tool_result_block(tool_use_id, [{"type": "text", "text": "ok"}])],
                },
            ],
            response_blocks=[{"type": "text", "text": "Done."}],
        ),
    ]


def test_request_and_response_messages_map_to_fragments() -> None:
    fragments = rounds_to_fragments([_round(round_id="0001", timestamp=1735689600.0)])
    kinds = [fragment.kind for fragment in fragments]

    assert kinds.count(FragmentKind.CONFIG_SNAPSHOT) == 1
    assert kinds.count(FragmentKind.AGENT_MESSAGE) == 2
    assert kinds.count(FragmentKind.MODEL_GENERATION) == 2


def test_thinking_is_redacted_by_default() -> None:
    fragments = rounds_to_fragments([_round(round_id="0001", timestamp=1735689600.0)])
    thinking = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("thinking_1")
    )

    assert thinking.payload["internal_reasoning"] == "opaque"
    assert set(thinking.payload["thinking"]) == {"sha256", "length"}


def test_store_thinking_preserves_content() -> None:
    fragments = rounds_to_fragments(
        [_round(round_id="0001", timestamp=1735689600.0)],
        AnthropicIngestOptions(store_thinking=True),
    )
    thinking = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("thinking_1")
    )
    assert thinking.payload["thinking"] == "private reasoning"


def test_tool_result_is_absorbed_into_preceding_tool_call() -> None:
    fragments = rounds_to_fragments(
        _tool_round("search_web", {"query": "refund policy"}, tool_use_id="tool_web")
    )
    tool = next(fragment for fragment in fragments if fragment.kind is FragmentKind.TOOL_CALL)

    assert tool.payload["tool_name"] == "search_web"
    assert tool.payload["result"] == [{"type": "text", "text": "ok"}]


def test_tool_result_error_emits_error_fragment() -> None:
    rounds = _tool_round("search_web", {"query": "refund policy"}, tool_use_id="tool_error")
    rounds[1]["request"]["messages"] = [
        {
            "role": "user",
            "content": [_tool_result_block("tool_error", {"message": "boom"}, is_error=True)],
        }
    ]
    fragments = rounds_to_fragments(rounds)
    error = next(fragment for fragment in fragments if fragment.kind is FragmentKind.ERROR)

    assert error.payload["error"] == {"message": "boom"}


def test_screenshot_tool_result_is_always_redacted() -> None:
    rounds = _tool_round("computer", {"action": "screenshot"}, tool_use_id="tool_screen")
    rounds[1]["request"]["messages"] = [
        {
            "role": "user",
            "content": [
                _tool_result_block(
                    "tool_screen",
                    [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "abcd1234",
                            },
                        }
                    ],
                )
            ],
        }
    ]
    fragments = rounds_to_fragments(rounds)
    tool = next(fragment for fragment in fragments if fragment.kind is FragmentKind.TOOL_CALL)

    redacted = tool.payload["result"][0]
    assert redacted["type"] == "image"
    assert set(redacted) >= {"sha256", "length", "media_type"}
    assert "data" not in redacted


def test_computer_screenshot_emits_tool_call_only() -> None:
    fragments = rounds_to_fragments(_tool_round("computer", {"action": "screenshot"}))
    kinds = [fragment.kind for fragment in fragments if "tool_1" in fragment.fragment_id]
    assert kinds == [FragmentKind.TOOL_CALL]


def test_computer_left_click_emits_state_mutation() -> None:
    fragments = rounds_to_fragments(
        _tool_round("computer", {"action": "left_click", "coordinate": [10, 20]})
    )
    kinds = [fragment.kind for fragment in fragments if "tool_1" in fragment.fragment_id]
    assert kinds == [FragmentKind.TOOL_CALL, FragmentKind.STATE_MUTATION]


def test_computer_type_emits_state_mutation() -> None:
    fragments = rounds_to_fragments(_tool_round("computer", {"action": "type", "text": "hello"}))
    assert any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_computer_key_emits_state_mutation() -> None:
    fragments = rounds_to_fragments(_tool_round("computer", {"action": "key", "text": "Enter"}))
    assert any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_computer_mouse_move_is_read_only() -> None:
    fragments = rounds_to_fragments(
        _tool_round("computer", {"action": "mouse_move", "coordinate": [10, 20]})
    )
    assert not any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_computer_scroll_is_read_only() -> None:
    fragments = rounds_to_fragments(
        _tool_round("computer", {"action": "scroll", "coordinate": [0, 10]})
    )
    assert not any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_computer_wait_is_read_only() -> None:
    fragments = rounds_to_fragments(_tool_round("computer", {"action": "wait", "duration": 1.0}))
    assert not any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_bash_command_is_destructive_by_default() -> None:
    fragments = rounds_to_fragments(_tool_round("bash", {"command": "rm -rf tmp"}))
    assert any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_bash_readonly_command_is_suppressed() -> None:
    fragments = rounds_to_fragments(_tool_round("bash", {"command": "ls -la"}))
    assert not any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_text_editor_replace_is_destructive() -> None:
    fragments = rounds_to_fragments(
        _tool_round("text_editor", {"action": "replace", "path": "a.txt"})
    )
    assert any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_text_editor_view_is_read_only() -> None:
    fragments = rounds_to_fragments(_tool_round("text_editor", {"action": "view", "path": "a.txt"}))
    assert not any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_policy_snapshot_metadata_override() -> None:
    fragments = rounds_to_fragments(
        [
            _round(
                round_id="0001",
                timestamp=1735689600.0,
                metadata={"user_id": "ops_1", "demm_kind": "policy_snapshot"},
            )
        ]
    )
    snapshot = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("request_snapshot")
    )

    assert snapshot.kind is FragmentKind.POLICY_SNAPSHOT
    assert snapshot.payload["constraint_activated"] is True


def test_human_approval_metadata_emits_human_fragment() -> None:
    fragments = rounds_to_fragments(
        [
            _round(
                round_id="0001",
                timestamp=1735689600.0,
                metadata={"user_id": "ops_1", "demm_human_approval": "approved"},
            )
        ]
    )
    assert any(fragment.kind is FragmentKind.HUMAN_APPROVAL for fragment in fragments)


def test_human_rejection_metadata_emits_human_fragment() -> None:
    fragments = rounds_to_fragments(
        [
            _round(
                round_id="0001",
                timestamp=1735689600.0,
                metadata={"user_id": "ops_1", "demm_human_approval": "rejected"},
            )
        ]
    )
    assert any(fragment.kind is FragmentKind.HUMAN_REJECTION for fragment in fragments)


def test_cross_stack_tools_regex_elevates_custom_tool() -> None:
    fragments = rounds_to_fragments(
        _tool_round("salesforce_sync", {"account_id": "acct-1"}),
        AnthropicIngestOptions(cross_stack_tools_pattern=r"salesforce_.*"),
    )
    tool = next(fragment for fragment in fragments if fragment.kind is FragmentKind.TOOL_CALL)
    assert tool.stack_tier is StackTier.CROSS_STACK


def test_state_mutation_tool_pattern_pairs_custom_tool() -> None:
    fragments = rounds_to_fragments(
        _tool_round("write_crm", {"account_id": "acct-1"}),
        AnthropicIngestOptions(state_mutation_tool_pattern=r"write_.*"),
    )
    assert any(
        fragment.kind is FragmentKind.STATE_MUTATION
        for fragment in fragments
        if "tool_1" in fragment.fragment_id
    )


def test_cache_control_is_absorbed_into_config_snapshot() -> None:
    rounds = [
        _round(
            round_id="0001",
            timestamp=1735689600.0,
            system=[
                {
                    "type": "text",
                    "text": "You are billing agent.",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        )
    ]
    fragments = rounds_to_fragments(rounds)
    snapshot = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )

    assert snapshot.payload["cache_control"] == [
        {"location": "system", "cache_control": {"type": "ephemeral"}}
    ]


def test_timestamp_parsing_accepts_iso_strings() -> None:
    fragments = rounds_to_fragments([_round(round_id="0001", timestamp="2025-01-01T00:00:00Z")])
    snapshot = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert snapshot.timestamp == 1735689600.0


def test_manifest_round_trip_reconstructs_fragments() -> None:
    manifest = rounds_to_manifest(
        [_round(round_id="0001", timestamp=1735689600.0)], scenario_id="anthropic_round_trip"
    )
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]

    assert manifest["architecture"] == "single_agent"
    assert fragments[0].parent_trace_id == "msg_0001"


def test_load_rounds_file_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                _round(round_id="0001", timestamp=1735689600.0),
                _round(round_id="0002", timestamp=1735689601.0),
            ]
        )
        + "\n"
    )

    rounds = load_rounds_file(path)

    assert len(rounds) == 2
    assert rounds[1]["round_id"] == "0002"
