"""Agent Framework adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reconstructor.adapters.agentframework import (
    AgentFrameworkIngestOptions,
    events_to_fragments,
    events_to_manifest,
    load_events_file,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _event(event_type: str, ts: object, **kwargs: object) -> dict[str, object]:
    payload = kwargs.pop("payload", None)
    record = {
        "ts": ts,
        "event_type": event_type,
        "message_id": kwargs.pop("message_id", f"msg_{event_type}"),
        "trace_id": kwargs.pop("trace_id", "trace-1"),
        "topic": kwargs.pop("topic", None),
        "sender": kwargs.pop("sender", None),
        "recipient": kwargs.pop("recipient", None),
        "payload": payload if payload is not None else kwargs,
    }
    return record


def _base_events() -> list[dict[str, object]]:
    return [
        _event(
            "speaker_selected",
            1735689600.0,
            message_id="speaker-1",
            sender="system",
            payload={"selected": "planner", "candidates": ["planner", "executor", "critic"]},
        ),
        _event(
            "message_published",
            1735689600.01,
            message_id="pub-1",
            sender="planner",
            recipient="research_topic",
            topic="research_topic",
            payload={"content": "Find the latest docs", "topic": "research_topic"},
        ),
        _event(
            "agent_called",
            1735689600.02,
            message_id="agent-1",
            sender="planner",
            recipient="executor",
            payload={
                "agent_id": "executor",
                "agent_name": "Executor",
                "input": {"task": "research"},
            },
        ),
        _event(
            "agent_returned",
            1735689600.03,
            message_id="agent-1-return",
            sender="executor",
            payload={
                "agent_id": "executor",
                "agent_name": "Executor",
                "output": {"summary": "done"},
            },
        ),
        _event(
            "tool_called",
            1735689600.04,
            message_id="tool-1",
            sender="executor",
            payload={
                "agent_id": "executor",
                "tool_name": "web_search",
                "args": {"query": "autogen docs"},
            },
        ),
        _event(
            "tool_returned",
            1735689600.05,
            message_id="tool-1-return",
            sender="executor",
            payload={
                "agent_id": "executor",
                "tool_name": "web_search",
                "result": [{"title": "AutoGen"}],
            },
        ),
        _event(
            "round_completed",
            1735689600.055,
            message_id="round-1",
            payload={"round_num": 1, "messages_in_round": 2},
        ),
        _event(
            "model_invocation",
            1735689600.06,
            message_id="model-1",
            sender="critic",
            payload={
                "agent_id": "critic",
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Review"}],
                "client_type": "azure_openai",
            },
        ),
        _event(
            "model_response",
            1735689600.07,
            message_id="model-1-return",
            sender="critic",
            payload={
                "agent_id": "critic",
                "model": "gpt-4o",
                "choices": [{"message": {"content": "Looks good"}}],
            },
        ),
        _event(
            "termination",
            1735689600.08,
            message_id="term-1",
            sender="planner",
            payload={"reason": "max_turns"},
        ),
    ]


def test_message_published_maps_to_agent_message() -> None:
    fragments = events_to_fragments(_base_events())
    published = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("published")
    )
    assert published.kind is FragmentKind.AGENT_MESSAGE
    assert published.payload["topic"] == "research_topic"


def test_agent_called_and_returned_pair_into_agent_message() -> None:
    fragments = events_to_fragments(_base_events())
    agent = next(fragment for fragment in fragments if fragment.fragment_id.endswith("agent_call"))
    assert agent.kind is FragmentKind.AGENT_MESSAGE
    assert agent.payload["output"] == {"summary": "done"}


def test_tool_called_and_returned_pair_into_tool_call() -> None:
    fragments = events_to_fragments(_base_events())
    tool = next(fragment for fragment in fragments if fragment.fragment_id.endswith("tool_call"))
    assert tool.kind is FragmentKind.TOOL_CALL
    assert tool.payload["result"] == [{"title": "AutoGen"}]


def test_state_mutation_regex_emits_state_fragment() -> None:
    fragments = events_to_fragments(
        _base_events(), AgentFrameworkIngestOptions(state_mutation_tool_pattern=r"web_.*")
    )
    state = next(fragment for fragment in fragments if fragment.fragment_id.endswith("tool_state"))
    assert state.kind is FragmentKind.STATE_MUTATION


def test_model_invocation_and_response_pair_into_model_generation() -> None:
    fragments = events_to_fragments(_base_events())
    model = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION
    )
    assert model.payload["model_id"] == "gpt-4o"
    assert model.payload["client_type"] == "azure_openai"


def test_speaker_selected_emits_manager_message() -> None:
    fragments = events_to_fragments(_base_events())
    speaker = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("speaker_selected")
    )
    assert speaker.actor_id == "manager"
    assert speaker.payload["selected"] == "planner"


def test_round_completed_is_absorbed_into_next_fragment() -> None:
    fragments = events_to_fragments(_base_events())
    model = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION
    )
    assert model.payload["round_context"] == {"round_num": 1, "messages_in_round": 2}
    assert not any(fragment.fragment_id.endswith("round_completed") for fragment in fragments)


def test_termination_emits_terminal_agent_message() -> None:
    fragments = events_to_fragments(_base_events())
    termination = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("termination")
    )
    assert termination.kind is FragmentKind.AGENT_MESSAGE
    assert termination.payload["terminal"] is True


def test_error_emits_error_fragment() -> None:
    events = _base_events() + [
        _event(
            "error",
            1735689600.09,
            message_id="err-1",
            sender="executor",
            payload={"error_type": "ValueError", "message": "boom"},
        )
    ]
    fragments = events_to_fragments(events)
    error = next(fragment for fragment in fragments if fragment.kind is FragmentKind.ERROR)
    assert error.payload["error"]["message"] == "boom"


def test_content_safety_decision_maps_to_policy_snapshot() -> None:
    events = _base_events() + [
        _event(
            "content_safety_decision",
            1735689600.085,
            message_id="safety-1",
            sender="system",
            payload={"policy": "block self-harm"},
        )
    ]
    fragments = events_to_fragments(events)
    policy = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.POLICY_SNAPSHOT
    )
    assert policy.payload["constraint_activated"] is True


def test_demm_kind_policy_snapshot_override() -> None:
    events = [
        _event(
            "message_published",
            1735689600.0,
            message_id="cfg-1",
            sender="planner",
            payload={"demm_kind": "policy_snapshot", "policy_id": "validator"},
        )
    ]
    fragments = events_to_fragments(events)
    assert fragments[0].kind is FragmentKind.POLICY_SNAPSHOT


def test_demm_kind_config_snapshot_override() -> None:
    events = [
        _event(
            "message_published",
            1735689600.0,
            message_id="cfg-1",
            sender="planner",
            payload={"demm_kind": "config_snapshot", "config": "v1"},
        )
    ]
    fragments = events_to_fragments(events)
    assert fragments[0].kind is FragmentKind.CONFIG_SNAPSHOT


def test_topic_filter_limits_ingested_events() -> None:
    fragments = events_to_fragments(
        _base_events(), AgentFrameworkIngestOptions(topic_filter=r"research_.*")
    )
    published = [fragment for fragment in fragments if fragment.fragment_id.endswith("published")]
    assert len(published) == 1


def test_auto_architecture_detects_multi_agent_via_speaker_selected() -> None:
    manifest = events_to_manifest(
        _base_events(), "af_multi", AgentFrameworkIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "multi_agent"


def test_auto_architecture_detects_multi_agent_via_agent_diversity() -> None:
    events = [event for event in _base_events() if event["event_type"] != "speaker_selected"] + [
        _event(
            "agent_called",
            1735689600.021,
            message_id="agent-2",
            sender="planner",
            recipient="critic",
            payload={"agent_id": "critic", "agent_name": "Critic", "input": {}},
        )
    ]
    manifest = events_to_manifest(
        events, "af_multi_agents", AgentFrameworkIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "multi_agent"


def test_auto_architecture_detects_human_in_the_loop() -> None:
    events = [
        _event(
            "agent_called",
            1735689600.0,
            sender="planner",
            payload={
                "agent_id": "human_proxy",
                "agent_name": "Human Proxy",
                "is_human_proxy": True,
            },
        )
    ]
    manifest = events_to_manifest(
        events, "af_hitl", AgentFrameworkIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "human_in_the_loop"


def test_auto_architecture_defaults_to_single_agent() -> None:
    events = [
        _event(
            "agent_called",
            1735689600.0,
            sender="planner",
            payload={"agent_id": "executor", "agent_name": "Executor", "input": {}},
        )
    ]
    manifest = events_to_manifest(
        events, "af_single", AgentFrameworkIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "single_agent"


def test_grpc_runtime_elevates_agent_messages_to_cross_stack() -> None:
    fragments = events_to_fragments(_base_events(), AgentFrameworkIngestOptions(runtime="grpc"))
    published = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("published")
    )
    assert published.stack_tier is StackTier.CROSS_STACK


def test_cross_stack_tool_regex_elevates_tool_call() -> None:
    fragments = events_to_fragments(
        _base_events(), AgentFrameworkIngestOptions(cross_stack_tools_pattern=r"web_.*")
    )
    tool = next(fragment for fragment in fragments if fragment.fragment_id.endswith("tool_call"))
    assert tool.stack_tier is StackTier.CROSS_STACK


def test_out_of_order_events_are_sorted_before_pairing() -> None:
    events = list(reversed(_base_events()))
    fragments = events_to_fragments(events)
    tool = next(fragment for fragment in fragments if fragment.fragment_id.endswith("tool_call"))
    assert tool.payload["result"] == [{"title": "AutoGen"}]


def test_legacy_v02_fields_are_accepted_with_warning() -> None:
    legacy = {
        "ts": 1735689600.0,
        "eventType": "agent_called",
        "messageId": "legacy-1",
        "traceId": "trace-legacy",
        "sender": "planner",
        "payload": {"agentId": "executor", "agentName": "Executor", "input": {}},
    }
    with pytest.deprecated_call():
        fragments = events_to_fragments([legacy])
    assert fragments[0].kind is FragmentKind.AGENT_MESSAGE


def test_unmatched_model_invocation_flushes_incomplete_fragment() -> None:
    events = [
        _event(
            "model_invocation",
            1735689600.0,
            sender="critic",
            payload={"agent_id": "critic", "model": "gpt-4o", "messages": []},
        )
    ]
    fragments = events_to_fragments(events)
    assert fragments[0].payload["incomplete"] is True


def test_manifest_round_trip_reconstructs_fragments() -> None:
    manifest = events_to_manifest(_base_events(), "af_roundtrip")
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]
    assert manifest["stack_tier"] == "within_stack"
    assert fragments[0].parent_trace_id == "trace-1"


def test_timestamp_parsing_accepts_iso8601() -> None:
    events = [
        _event(
            "message_published", "2026-04-27T12:00:00Z", sender="planner", payload={"content": "hi"}
        )
    ]
    fragments = events_to_fragments(events)
    assert fragments[0].timestamp == 1777291200.0


def test_jsonl_loader_accepts_line_delimited_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in _base_events()) + "\n")
    events = load_events_file(path)
    assert len(events) == len(_base_events())
