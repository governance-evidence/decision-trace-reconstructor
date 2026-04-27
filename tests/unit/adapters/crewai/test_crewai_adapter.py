"""CrewAI adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.adapters.crewai import (
    CrewAIIngestOptions,
    events_to_fragments,
    events_to_manifest,
    load_events_file,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _event(event_type: str, ts: object, **payload: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "timestamp": ts,
        "payload": payload,
    }


def _base_events() -> list[dict[str, object]]:
    return [
        _event(
            "crew_kickoff_started",
            "2026-04-27T12:00:00Z",
            crew_name="Editorial Crew",
            agents=[{"role": "Researcher"}, {"role": "Writer"}],
            tasks=[{"id": "task-1", "description": "Research"}],
            process="hierarchical",
        ),
        _event(
            "manager_agent_invoked",
            1735752000.01,
            crew_name="Editorial Crew",
            task="Research the topic",
        ),
        _event(
            "task_started",
            1735752000.02,
            crew_name="Editorial Crew",
            task_id="task-1",
            task_description="Research the topic",
            assigned_agent="Researcher",
            expected_output="Bullet notes",
        ),
        _event(
            "tool_usage_started",
            1735752000.03,
            crew_name="Editorial Crew",
            agent_role="Researcher",
            tool_name="web_search",
            args={"query": "CrewAI telemetry"},
        ),
        _event(
            "tool_usage_finished",
            1735752000.04,
            crew_name="Editorial Crew",
            agent_role="Researcher",
            tool_name="web_search",
            output=[{"title": "CrewAI docs"}],
        ),
        _event(
            "llm_call_started",
            1735752000.05,
            crew_name="Editorial Crew",
            agent_role="Researcher",
            model="gpt-4.1",
            messages=[{"role": "user", "content": "Summarize docs"}],
        ),
        _event(
            "agent_logs_execution",
            1735752000.055,
            crew_name="Editorial Crew",
            agent_role="Researcher",
            text="Thinking through the evidence",
        ),
        _event(
            "llm_call_completed",
            1735752000.06,
            crew_name="Editorial Crew",
            agent_role="Researcher",
            model="gpt-4.1",
            output="Need a writer pass",
            tokens=123,
        ),
        _event(
            "delegation",
            1735752000.07,
            crew_name="Editorial Crew",
            from_agent="Researcher",
            to_agent="Writer",
            task="Write final markdown",
        ),
        _event(
            "tool_usage_started",
            1735752000.08,
            crew_name="Editorial Crew",
            tool_name="markdown_formatter",
            args={"style": "concise"},
        ),
        _event(
            "tool_usage_finished",
            1735752000.09,
            crew_name="Editorial Crew",
            tool_name="markdown_formatter",
            output="formatted markdown",
        ),
        _event(
            "memory_query_started",
            1735752000.10,
            crew_name="Editorial Crew",
            agent_role="Writer",
            query="prior summary",
            memory_type="long_term",
        ),
        _event(
            "memory_query_completed",
            1735752000.11,
            crew_name="Editorial Crew",
            agent_role="Writer",
            memory_type="long_term",
            results=[{"snippet": "Prior note"}],
        ),
        _event(
            "demm_policy_snapshot",
            1735752000.12,
            crew_name="Editorial Crew",
            agent_role="Writer",
            policy_id="safety_checker",
        ),
        _event(
            "consensual_vote_cast",
            1735752000.13,
            crew_name="Editorial Crew",
            agent_role="Writer",
            proposal="Ship summary",
            vote="approve",
        ),
    ]


def test_crew_kickoff_started_emits_config_snapshot() -> None:
    fragments = events_to_fragments(_base_events())
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert config.payload["process"] == "hierarchical"
    assert len(config.payload["agents"]) == 2


def test_agent_execution_boundaries_emit_agent_messages() -> None:
    fragments = events_to_fragments(_base_events())
    task_message = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("task_started")
    )
    assert task_message.kind is FragmentKind.AGENT_MESSAGE
    assert task_message.actor_id == "Researcher"


def test_tool_usage_pair_maps_to_tool_call() -> None:
    fragments = events_to_fragments(
        _base_events(), CrewAIIngestOptions(cross_stack_tools_pattern=r"web_search")
    )
    tool = next(
        fragment
        for fragment in fragments
        if fragment.fragment_id.endswith("tool_call")
        and fragment.payload["tool_name"] == "web_search"
    )
    assert tool.kind is FragmentKind.TOOL_CALL
    assert tool.payload["result"] == [{"title": "CrewAI docs"}]
    assert tool.stack_tier is StackTier.CROSS_STACK


def test_tool_usage_error_emits_paired_error() -> None:
    events = _base_events() + [
        _event(
            "tool_usage_started",
            1735752000.14,
            crew_name="Editorial Crew",
            agent_role="Writer",
            tool_name="publish",
            args={"channel": "blog"},
        ),
        _event(
            "tool_usage_error",
            1735752000.15,
            crew_name="Editorial Crew",
            agent_role="Writer",
            tool_name="publish",
            error="denied",
        ),
    ]
    fragments = events_to_fragments(events)
    error = next(fragment for fragment in fragments if fragment.fragment_id.endswith("tool_error"))
    assert error.kind is FragmentKind.ERROR
    assert error.payload["error"] == "denied"


def test_state_mutation_regex_emits_state_fragment() -> None:
    fragments = events_to_fragments(
        _base_events(), CrewAIIngestOptions(state_mutation_tool_pattern=r"markdown_.*")
    )
    mutation = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("tool_state")
    )
    assert mutation.kind is FragmentKind.STATE_MUTATION
    assert mutation.payload["tool_name"] == "markdown_formatter"


def test_llm_pair_maps_to_model_generation() -> None:
    fragments = events_to_fragments(_base_events())
    llm = next(fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION)
    assert llm.payload["model_id"] == "gpt-4.1"
    assert llm.payload["token_count"] == 123


def test_agent_logs_are_absorbed_into_model_generation() -> None:
    fragments = events_to_fragments(_base_events())
    llm = next(fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION)
    assert "Thinking through the evidence" in llm.payload["agent_visible_log"]


def test_missing_llm_completion_emits_incomplete_model_generation() -> None:
    events = [event for event in _base_events() if event["event_type"] != "llm_call_completed"]
    fragments = events_to_fragments(events)
    llm = next(fragment for fragment in fragments if fragment.kind is FragmentKind.MODEL_GENERATION)
    assert llm.payload["incomplete"] is True


def test_delegation_switches_actor_for_subsequent_fragments() -> None:
    fragments = events_to_fragments(_base_events())
    formatter = next(
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.TOOL_CALL
        and fragment.payload["tool_name"] == "markdown_formatter"
    )
    assert formatter.actor_id == "Writer"


def test_memory_query_maps_to_retrieval_result() -> None:
    fragments = events_to_fragments(_base_events())
    retrieval = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.RETRIEVAL_RESULT
    )
    assert retrieval.payload["retrieved"] == [{"snippet": "Prior note"}]


def test_long_term_memory_is_cross_stack() -> None:
    fragments = events_to_fragments(_base_events())
    retrieval = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.RETRIEVAL_RESULT
    )
    assert retrieval.stack_tier is StackTier.CROSS_STACK


def test_manager_agent_invoked_uses_synthetic_manager_actor() -> None:
    fragments = events_to_fragments(_base_events())
    manager = next(
        fragment for fragment in fragments if fragment.fragment_id.endswith("manager_invoked")
    )
    assert manager.actor_id == "Manager"


def test_consensual_vote_emits_agent_message() -> None:
    fragments = events_to_fragments(_base_events())
    vote = next(fragment for fragment in fragments if fragment.fragment_id.endswith("vote"))
    assert vote.kind is FragmentKind.AGENT_MESSAGE
    assert vote.payload["vote"] == "approve"


def test_custom_policy_event_maps_to_policy_snapshot() -> None:
    fragments = events_to_fragments(_base_events())
    policy = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.POLICY_SNAPSHOT
    )
    assert policy.payload["policy_id"] == "safety_checker"


def test_scope_failures_map_to_error() -> None:
    events = _base_events() + [
        _event(
            "task_failed",
            1735752000.2,
            crew_name="Editorial Crew",
            agent_role="Writer",
            error="task exploded",
        )
    ]
    fragments = events_to_fragments(events)
    error = next(fragment for fragment in fragments if fragment.fragment_id.endswith("scope_error"))
    assert error.kind is FragmentKind.ERROR


def test_auto_architecture_infers_multi_agent() -> None:
    manifest = events_to_manifest(
        _base_events(), "crewai_multi", CrewAIIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "multi_agent"


def test_auto_architecture_infers_single_agent() -> None:
    events = [
        _event(
            "crew_kickoff_started",
            1735752000.0,
            crew_name="Solo Crew",
            agents=[{"role": "Solo"}],
            tasks=[{"id": "task-1", "description": "Write"}],
            process="sequential",
        ),
        _event(
            "task_started",
            1735752000.1,
            crew_name="Solo Crew",
            task_id="task-1",
            assigned_agent="Solo",
        ),
    ]
    manifest = events_to_manifest(
        events, "crewai_single", CrewAIIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "single_agent"


def test_auto_architecture_infers_human_in_the_loop() -> None:
    events = [
        _event(
            "crew_kickoff_started",
            1735752000.0,
            crew_name="Review Crew",
            agents=[{"role": "Reviewer"}],
            tasks=[{"id": "task-1", "description": "Review", "human_input": True}],
            process="sequential",
        )
    ]
    manifest = events_to_manifest(
        events, "crewai_hitl", CrewAIIngestOptions(auto_architecture=True)
    )
    assert manifest["architecture"] == "human_in_the_loop"


def test_emit_config_snapshot_can_be_disabled() -> None:
    fragments = events_to_fragments(_base_events(), CrewAIIngestOptions(emit_config_snapshot=False))
    assert not any(fragment.kind is FragmentKind.CONFIG_SNAPSHOT for fragment in fragments)


def test_crew_name_filter_limits_fragments() -> None:
    events = _base_events() + [
        _event(
            "task_started",
            1735752001.0,
            crew_name="Other Crew",
            task_id="task-z",
            assigned_agent="Other",
        )
    ]
    fragments = events_to_fragments(events, CrewAIIngestOptions(crew_name="Editorial Crew"))
    assert all(fragment.parent_trace_id == "Editorial Crew" for fragment in fragments)


def test_manifest_round_trip_reconstructs_fragments() -> None:
    manifest = events_to_manifest(_base_events(), "crewai_roundtrip")
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]
    assert manifest["stack_tier"] == "within_stack"
    assert fragments[0].parent_trace_id == "Editorial Crew"


def test_timestamp_parsing_accepts_iso8601() -> None:
    fragments = events_to_fragments(_base_events())
    config = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.CONFIG_SNAPSHOT
    )
    assert config.timestamp == 1777291200.0


def test_jsonl_loader_accepts_line_delimited_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in _base_events()) + "\n")
    events = load_events_file(path)
    assert len(events) == len(_base_events())


def test_jsonl_loader_assigns_stable_unique_event_ids(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in _base_events()) + "\n")

    events = load_events_file(path)

    assert [event["event_id"] for event in events[:3]] == [
        "event_0001",
        "event_0002",
        "event_0003",
    ]
    assert len({event["event_id"] for event in events}) == len(events)
