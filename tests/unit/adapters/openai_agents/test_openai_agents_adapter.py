"""OpenAI Agents adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.adapters.openai_agents import (
    OpenAIAgentsIngestOptions,
    load_traces_file,
    trace_to_fragments,
    trace_to_manifest,
    traces_to_manifests,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _trace_payload(trace_id: str = "trace_abc123") -> dict[str, object]:
    return {
        "trace_id": trace_id,
        "workflow_name": "customer_support_workflow",
        "group_id": "conversation-1",
        "metadata": {"sdk_version": "1.2.0"},
        "spans": [
            {
                "span_id": "span-agent",
                "trace_id": trace_id,
                "parent_id": None,
                "started_at": "2025-04-15T09:00:00Z",
                "ended_at": "2025-04-15T09:00:01Z",
                "span_data": {
                    "type": "agent",
                    "name": "triage_agent",
                    "input": {"text": "Need help with a refund"},
                    "output": {"status": "triaged"},
                },
                "error": None,
            },
            {
                "span_id": "span-guardrail",
                "trace_id": trace_id,
                "parent_id": "span-agent",
                "started_at": "2025-04-15T09:00:00.100000Z",
                "ended_at": "2025-04-15T09:00:00.150000Z",
                "span_data": {
                    "type": "guardrail",
                    "name": "input_guardrail",
                    "result": "passed",
                },
                "error": None,
            },
            {
                "span_id": "span-response",
                "trace_id": trace_id,
                "parent_id": "span-agent",
                "started_at": "2025-04-15T09:00:01Z",
                "ended_at": "2025-04-15T09:00:02Z",
                "span_data": {
                    "type": "response",
                    "model": "gpt-4.1-mini",
                    "input": {"messages": [{"role": "user", "content": "Need help with a refund"}]},
                    "output": {
                        "text": "Let me check the policy.",
                        "reasoning": "billing policy reasoning",
                    },
                    "input_tokens": 12,
                    "output_tokens": 7,
                },
                "error": None,
            },
            {
                "span_id": "span-web",
                "trace_id": trace_id,
                "parent_id": "span-agent",
                "started_at": "2025-04-15T09:00:02Z",
                "ended_at": "2025-04-15T09:00:03Z",
                "span_data": {
                    "type": "web_search",
                    "tool_name": "web_search",
                    "input": {"query": "refund policy"},
                    "output": [{"title": "Refund policy", "url": "https://example.test/refunds"}],
                },
                "error": None,
            },
            {
                "span_id": "span-handoff",
                "trace_id": trace_id,
                "parent_id": "span-agent",
                "started_at": "2025-04-15T09:00:03Z",
                "ended_at": "2025-04-15T09:00:03.100000Z",
                "span_data": {
                    "type": "handoff",
                    "handoff_to": "billing_agent",
                    "input": {"reason": "refund requires billing agent"},
                },
                "error": None,
            },
            {
                "span_id": "span-function",
                "trace_id": trace_id,
                "parent_id": "span-handoff",
                "started_at": "2025-04-15T09:00:04Z",
                "ended_at": "2025-04-15T09:00:04.500000Z",
                "span_data": {
                    "type": "function",
                    "tool_name": "write_refund",
                    "input": {"order_id": "A100"},
                    "output": {"status": "submitted"},
                },
                "error": None,
            },
            {
                "span_id": "span-file-search",
                "trace_id": trace_id,
                "parent_id": "span-handoff",
                "started_at": 1744707605,
                "ended_at": 1744707605.5,
                "span_data": {
                    "type": "file_search",
                    "tool_name": "file_search",
                    "input": {"query": "customer refund history"},
                    "output": [{"file_id": "file-1", "snippet": "Courtesy refund in 2024"}],
                },
                "error": None,
            },
            {
                "span_id": "span-computer",
                "trace_id": trace_id,
                "parent_id": "span-handoff",
                "started_at": "2025-04-15T09:00:06Z",
                "ended_at": "2025-04-15T09:00:06.500000Z",
                "span_data": {
                    "type": "computer_use",
                    "tool_name": "computer_use",
                    "input": {"action": "click", "target": "refund-button"},
                    "output": {"status": "clicked"},
                },
                "error": None,
            },
            {
                "span_id": "span-custom",
                "trace_id": trace_id,
                "parent_id": "span-handoff",
                "started_at": "2025-04-15T09:00:07Z",
                "ended_at": "2025-04-15T09:00:07.100000Z",
                "span_data": {
                    "type": "custom",
                    "name": "model_config",
                    "input": {"temperature": 0},
                    "metadata": {"demm_kind": "config_snapshot"},
                },
                "error": None,
            },
        ],
    }


def test_openai_agents_maps_supported_span_types() -> None:
    fragments = trace_to_fragments(
        _trace_payload(),
        OpenAIAgentsIngestOptions(state_mutation_tool_pattern=r"write_.*"),
    )
    kinds = [fragment.kind for fragment in fragments]

    assert FragmentKind.AGENT_MESSAGE in kinds
    assert FragmentKind.POLICY_SNAPSHOT in kinds
    assert FragmentKind.MODEL_GENERATION in kinds
    assert FragmentKind.TOOL_CALL in kinds
    assert FragmentKind.RETRIEVAL_RESULT in kinds
    assert FragmentKind.STATE_MUTATION in kinds
    assert FragmentKind.CONFIG_SNAPSHOT in kinds


def test_web_search_always_elevates_to_cross_stack() -> None:
    fragments = trace_to_fragments(_trace_payload())
    web_tool = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("span-web_web_tool")
    )
    retrieval = next(
        fragment
        for fragment in fragments
        if fragment.fragment_id.endswith("span-web_web_retrieval")
    )

    assert web_tool.stack_tier is StackTier.CROSS_STACK
    assert retrieval.stack_tier is StackTier.CROSS_STACK


def test_computer_use_always_pairs_state_mutation() -> None:
    fragments = trace_to_fragments(_trace_payload())
    computer = [fragment for fragment in fragments if "span-computer" in fragment.fragment_id]

    assert [fragment.kind for fragment in computer] == [
        FragmentKind.TOOL_CALL,
        FragmentKind.STATE_MUTATION,
    ]
    assert all(fragment.stack_tier is StackTier.CROSS_STACK for fragment in computer)


def test_handoff_switches_actor_for_child_spans() -> None:
    fragments = trace_to_fragments(
        _trace_payload(),
        OpenAIAgentsIngestOptions(state_mutation_tool_pattern=r"write_.*"),
    )
    write_tool = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("span-function_tool")
    )

    assert write_tool.actor_id == "billing_agent"


def test_handoff_triggers_multi_agent_auto_architecture() -> None:
    manifest = trace_to_manifest(
        _trace_payload(),
        scenario_id="openai_handoff",
        opts=OpenAIAgentsIngestOptions(auto_architecture=True),
    )

    assert manifest["architecture"] == "multi_agent"


def test_distinct_agent_names_trigger_multi_agent_auto_architecture() -> None:
    payload = _trace_payload(trace_id="c4b7e6f2-8db8-4eab-9e07-c90eb9ca4ad7")
    payload["spans"].append(
        {
            "span_id": "span-agent-2",
            "trace_id": payload["trace_id"],
            "parent_id": None,
            "started_at": "2025-04-15T09:00:08Z",
            "ended_at": "2025-04-15T09:00:09Z",
            "span_data": {"type": "agent", "name": "billing_agent"},
            "error": None,
        }
    )

    manifest = trace_to_manifest(
        payload,
        scenario_id="openai_two_agents",
        opts=OpenAIAgentsIngestOptions(auto_architecture=True),
    )

    assert manifest["architecture"] == "multi_agent"


def test_guardrail_passed_maps_constraint_true() -> None:
    fragments = trace_to_fragments(_trace_payload())
    policy = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.POLICY_SNAPSHOT
    )
    assert policy.payload["constraint_activated"] is True


def test_guardrail_failed_maps_constraint_false() -> None:
    payload = _trace_payload()
    payload["spans"][1]["span_data"]["result"] = "failed"
    fragments = trace_to_fragments(payload)
    policy = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.POLICY_SNAPSHOT
    )
    assert policy.payload["constraint_activated"] is False
    assert policy.payload["result"] == "failed"


def test_reasoning_is_redacted_by_default() -> None:
    fragments = trace_to_fragments(_trace_payload())
    model = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION
    )

    assert model.payload["internal_reasoning"] == "opaque"
    assert "reasoning_summary" not in model.payload
    assert model.payload["reasoning_summary_length"] == len("billing policy reasoning")


def test_store_reasoning_preserves_summary() -> None:
    fragments = trace_to_fragments(
        _trace_payload(),
        OpenAIAgentsIngestOptions(store_reasoning=True),
    )
    model = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION
    )
    assert model.payload["reasoning_summary"] == "billing policy reasoning"


def test_trace_id_formats_and_epoch_timestamps_are_accepted() -> None:
    fragments = trace_to_fragments(_trace_payload(trace_id="0f0d63f0-0cee-4f56-8ca4-8d610ca53cff"))
    file_search = next(
        fragment
        for fragment in fragments
        if fragment.fragment_id.endswith("span-file-search_file_search")
    )

    assert file_search.parent_trace_id == "0f0d63f0-0cee-4f56-8ca4-8d610ca53cff"
    assert file_search.timestamp == 1744707605.0


def test_group_id_merge_emits_single_manifest() -> None:
    traces = [_trace_payload("trace_a"), _trace_payload("trace_b")]
    manifests = traces_to_manifests(
        traces,
        scenario_id_prefix="openai_group",
        group_into_scenarios=True,
    )

    assert len(manifests) == 1
    assert manifests[0]["scenario_id"] == "openai_group_1"
    assert len(manifests[0]["fragments"]) > len(trace_to_manifest(traces[0], "one")["fragments"])


def test_manifest_round_trip_reconstructs_fragments() -> None:
    manifest = trace_to_manifest(_trace_payload(), scenario_id="openai_round_trip")
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]

    assert fragments[0].parent_trace_id == "trace_abc123"
    assert fragments[-1].kind in {FragmentKind.CONFIG_SNAPSHOT, FragmentKind.STATE_MUTATION}


def test_error_field_emits_error_fragment() -> None:
    payload = _trace_payload()
    payload["spans"][5]["error"] = "refund API timed out"
    fragments = trace_to_fragments(payload)
    error = next(fragment for fragment in fragments if fragment.kind is FragmentKind.ERROR)

    assert error.payload["error"] == "refund API timed out"


def test_load_traces_file_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "openai_agents.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(item) for item in [_trace_payload("trace_1"), _trace_payload("trace_2")]
        )
        + "\n"
    )

    traces = load_traces_file(path)

    assert len(traces) == 2
    assert traces[1]["trace_id"] == "trace_2"
