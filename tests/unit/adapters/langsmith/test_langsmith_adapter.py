"""LangSmith adapter mapping tests.

Pure-mapping tests using hand-crafted run dicts. No network. The
``langsmith`` SDK is not required to import the adapter for these tests
because the mapping path is dict-driven; only the ``fetch_*`` helpers need
the SDK at call time.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reconstructor.adapters.langsmith import (
    LangSmithIngestOptions,
    runs_to_fragments,
    runs_to_manifest,
)
from reconstructor.core.fragment import FragmentKind, StackTier


def _run(
    rid: str,
    run_type: str,
    name: str = "node",
    *,
    start: str = "2025-01-01T00:00:00Z",
    inputs: dict | None = None,
    outputs: dict | None = None,
    error: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    parent: str | None = None,
) -> dict:
    """Build a minimal LangSmith run dict for tests."""
    return {
        "id": rid,
        "name": name,
        "run_type": run_type,
        "start_time": start,
        "end_time": "2025-01-01T00:00:01Z",
        "inputs": inputs or {},
        "outputs": outputs or {},
        "error": error,
        "tags": tags or [],
        "extra": {"metadata": metadata or {}},
        "events": [],
        "trace_id": "trace-001",
        "parent_run_id": parent,
        "session_id": None,
        "status": "success",
    }


# ---------------------------------------------------------------------------
# RunType -> FragmentKind mapping (all 7 paths).
# ---------------------------------------------------------------------------


def test_llm_run_maps_to_model_generation() -> None:
    runs = [_run("r1", "llm", name="ChatOpenAI")]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.MODEL_GENERATION
    assert frags[0].payload["model_id"] == "ChatOpenAI"
    assert frags[0].payload["internal_reasoning"] == "opaque"


def test_tool_run_maps_to_tool_call() -> None:
    runs = [_run("r1", "tool", name="search_web", inputs={"query": "x"})]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.TOOL_CALL
    assert frags[0].payload["tool_name"] == "search_web"
    assert frags[0].payload["args"] == {"query": "x"}


def test_retriever_run_maps_to_retrieval_result() -> None:
    runs = [_run("r1", "retriever", name="VectorStore", outputs={"docs": [1, 2]})]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.RETRIEVAL_RESULT


def test_chain_run_maps_to_agent_message() -> None:
    runs = [_run("r1", "chain", name="planner_agent")]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.AGENT_MESSAGE


def test_prompt_run_maps_to_agent_message() -> None:
    runs = [_run("r1", "prompt", name="system_prompt")]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.AGENT_MESSAGE


def test_parser_run_is_skipped() -> None:
    runs = [_run("r1", "parser", name="OutputParser")]
    frags = runs_to_fragments(runs)
    assert frags == []


def test_embedding_run_is_skipped() -> None:
    runs = [_run("r1", "embedding", name="OpenAIEmbeddings")]
    frags = runs_to_fragments(runs)
    assert frags == []


def test_skip_rules_are_configurable() -> None:
    """When skip_run_types is empty, parser/embedding runs do emit fragments
    (mapped through the catch-all chain branch)."""
    runs = [_run("r1", "parser", name="OutputParser")]
    opts = LangSmithIngestOptions(skip_run_types=())
    frags = runs_to_fragments(runs, opts)
    # parser falls through none of the explicit run_type branches; nothing emitted.
    assert frags == []


# ---------------------------------------------------------------------------
# Human-node detection (chain runs flagged as human approval / rejection).
# ---------------------------------------------------------------------------


def test_chain_run_with_human_node_metadata_is_human_approval() -> None:
    runs = [
        _run(
            "r1",
            "chain",
            name="approval_gate",
            metadata={"langgraph_node": "human_approval"},
        )
    ]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.HUMAN_APPROVAL
    assert frags[0].stack_tier is StackTier.HUMAN


def test_chain_run_with_human_node_and_error_is_human_rejection() -> None:
    runs = [
        _run(
            "r1",
            "chain",
            name="hitl_node",
            error="operator rejected the action",
        )
    ]
    frags = runs_to_fragments(runs)
    assert len(frags) == 2  # human_rejection + error
    assert frags[0].kind is FragmentKind.HUMAN_REJECTION
    assert frags[1].kind is FragmentKind.ERROR


# ---------------------------------------------------------------------------
# State-mutation heuristic.
# ---------------------------------------------------------------------------


def test_state_mutation_heuristic_emits_paired_fragment() -> None:
    runs = [_run("r1", "tool", name="db_exec", inputs={"sql": "DROP TABLE x"})]
    opts = LangSmithIngestOptions(
        state_mutation_tool_pattern=r"(write|exec|drop|delete)",
    )
    frags = runs_to_fragments(runs, opts)
    assert len(frags) == 2
    assert frags[0].kind is FragmentKind.TOOL_CALL
    assert frags[1].kind is FragmentKind.STATE_MUTATION
    assert frags[1].payload["state_change_magnitude"] == 1.0
    # State mutation fragment is timestamped 1 ms after the tool call to
    # preserve temporal ordering.
    assert frags[1].timestamp > frags[0].timestamp


def test_state_mutation_heuristic_disabled_by_default() -> None:
    runs = [_run("r1", "tool", name="db_exec")]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.TOOL_CALL


def test_state_mutation_heuristic_does_not_match_innocuous_tools() -> None:
    runs = [_run("r1", "tool", name="search_web")]
    opts = LangSmithIngestOptions(
        state_mutation_tool_pattern=r"(write|exec|drop|delete)",
    )
    frags = runs_to_fragments(runs, opts)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.TOOL_CALL


# ---------------------------------------------------------------------------
# Tag-driven policy / config snapshots (operator opt-in).
# ---------------------------------------------------------------------------


def test_policy_snapshot_tag_emits_policy_snapshot_fragment() -> None:
    runs = [_run("r1", "chain", name="policy_check", tags=["policy_snapshot"])]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.POLICY_SNAPSHOT
    assert frags[0].payload["constraint_activated"] is True


def test_config_snapshot_tag_emits_config_snapshot_fragment() -> None:
    runs = [_run("r1", "chain", name="boot_config", tags=["config_snapshot"])]
    frags = runs_to_fragments(runs)
    assert len(frags) == 1
    assert frags[0].kind is FragmentKind.CONFIG_SNAPSHOT


# ---------------------------------------------------------------------------
# Error fragments are always emitted alongside the primary fragment.
# ---------------------------------------------------------------------------


def test_error_in_llm_run_emits_error_fragment_after_model_generation() -> None:
    runs = [
        _run("r1", "llm", name="ChatOpenAI", error="rate limit"),
    ]
    frags = runs_to_fragments(runs)
    assert len(frags) == 2
    assert frags[0].kind is FragmentKind.MODEL_GENERATION
    assert frags[1].kind is FragmentKind.ERROR
    assert frags[1].payload["error"] == "rate limit"


# ---------------------------------------------------------------------------
# actor_id derivation.
# ---------------------------------------------------------------------------


def test_actor_id_uses_langgraph_node_when_present() -> None:
    runs = [
        _run(
            "r1",
            "tool",
            name="generic_tool",
            metadata={"langgraph_node": "executor"},
        )
    ]
    frags = runs_to_fragments(runs)
    assert frags[0].actor_id == "executor"


def test_actor_id_falls_back_to_run_name() -> None:
    runs = [_run("r1", "tool", name="search_web")]
    frags = runs_to_fragments(runs)
    assert frags[0].actor_id == "search_web"


def test_actor_override_pins_actor_id_for_whole_trace() -> None:
    runs = [
        _run("r1", "tool", name="search_web"),
        _run("r2", "llm", name="ChatOpenAI", start="2025-01-01T00:00:02Z"),
    ]
    opts = LangSmithIngestOptions(actor_override="primary_agent")
    frags = runs_to_fragments(runs, opts)
    assert all(f.actor_id == "primary_agent" for f in frags)


# ---------------------------------------------------------------------------
# Cross-stack tag elevates per-fragment tier.
# ---------------------------------------------------------------------------


def test_cross_stack_tag_elevates_fragment_tier() -> None:
    runs = [_run("r1", "tool", name="external_mcp_call", tags=["cross_stack"])]
    opts = LangSmithIngestOptions(stack_tier=StackTier.WITHIN_STACK)
    frags = runs_to_fragments(runs, opts)
    assert frags[0].stack_tier is StackTier.CROSS_STACK


# ---------------------------------------------------------------------------
# Ordering: fragments come back in start-time order regardless of input order.
# ---------------------------------------------------------------------------


def test_fragments_are_emitted_in_start_time_order() -> None:
    runs = [
        _run("r2", "llm", name="m", start="2025-01-01T00:00:02Z"),
        _run("r1", "tool", name="t", start="2025-01-01T00:00:00Z"),
        _run("r3", "chain", name="c", start="2025-01-01T00:00:01Z"),
    ]
    frags = runs_to_fragments(runs)
    assert [f.fragment_id.endswith(s) for f, s in zip(frags, ("tool", "msg", "llm"), strict=True)]
    timestamps = [f.timestamp for f in frags]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# runs_to_manifest produces a complete fragments.json shape.
# ---------------------------------------------------------------------------


def test_runs_to_manifest_produces_full_manifest_shape() -> None:
    runs = [_run("r1", "llm", name="ChatOpenAI")]
    manifest = runs_to_manifest(
        runs,
        scenario_id="my_scenario",
        opts=LangSmithIngestOptions(
            architecture="multi_agent",
            stack_tier=StackTier.CROSS_STACK,
        ),
    )
    assert manifest["scenario_id"] == "my_scenario"
    assert manifest["architecture"] == "multi_agent"
    assert manifest["stack_tier"] == "cross_stack"
    assert len(manifest["fragments"]) == 1
    f = manifest["fragments"][0]
    assert f["kind"] == "model_generation"
    assert f["stack_tier"] == "cross_stack"


# ---------------------------------------------------------------------------
# Timestamp parsing accepts ISO strings, datetimes, and floats.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ts_value",
    [
        "2025-01-01T00:00:00Z",
        "2025-01-01T00:00:00+00:00",
        datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        1735689600.0,  # 2025-01-01T00:00:00Z
    ],
)
def test_timestamp_parsing_accepts_multiple_forms(ts_value: object) -> None:
    runs = [_run("r1", "llm", name="ChatOpenAI", start=ts_value)]  # type: ignore[arg-type]
    frags = runs_to_fragments(runs)
    assert frags[0].timestamp == pytest.approx(1735689600.0)
