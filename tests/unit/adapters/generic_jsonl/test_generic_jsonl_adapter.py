"""Generic JSONL adapter mapping tests."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from reconstructor.adapters.generic_jsonl import (
    GenericJsonlIngestOptions,
    iter_jsonl_stream,
    load_mapping_file,
    load_records_file,
    records_to_fragments,
    records_to_manifest,
    validate_mapping_sample,
)
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier


def _mapping_yaml() -> str:
    return """
schema_version: "1.0"
source_name: homegrown_agent
fields:
  fragment_id: id
  timestamp: ts
  actor_id: metadata.actor.id
  payload: null
kind_field: kind
kind_map:
  prompt: agent_message
  llm: model_generation
  tool: tool_call
  retrieval: retrieval_result
  state_change: state_mutation
  policy_check: policy_snapshot
  config_emit: config_snapshot
  human_decision: human_approval
  error: error
  final: agent_message
skip_kinds: [heartbeat, internal, debug]
state_mutation_predicate:
  field: tool
  matches_regex: (write|exec|drop|delete|update|insert|push|publish)
absorb_followups:
  tool_result:
    absorbed_by_kind: tool
    payload_key: result
    pair_match_field: id
    parent_match_field: parent_id
stack_tier_field: tier
stack_tier_default: within_stack
architecture: auto
""".strip()


def _records() -> list[dict[str, object]]:
    return [
        {
            "id": "e1",
            "ts": 1735689600.0,
            "kind": "prompt",
            "content": "Need report",
            "metadata": {"actor": {"id": "main"}},
        },
        {
            "id": "e2",
            "ts": 1735689601,
            "kind": "llm",
            "model": "gpt-4o",
            "metadata": {"actor": {"id": "main"}},
        },
        {
            "id": "e3",
            "ts": "2025-01-01T00:00:02Z",
            "kind": "tool",
            "tool": "write_report",
            "args": {"path": "/tmp/report.md"},
            "metadata": {"actor": {"id": "main"}},
            "tier": "cross_stack",
        },
        {
            "id": "e4",
            "ts": 1735689603.0,
            "kind": "tool_result",
            "parent_id": "e3",
            "result": {"ok": True},
            "metadata": {"actor": {"id": "main"}},
        },
        {
            "id": "e5",
            "ts": 1735689604.0,
            "kind": "human_decision",
            "decision": "DENIED by reviewer",
            "metadata": {"actor": {"id": "supervisor"}},
        },
        {
            "id": "e6",
            "ts": 1735689605.0,
            "kind": "heartbeat",
            "metadata": {"actor": {"id": "main"}},
        },
    ]


def test_mapping_yaml_subset_loader_supports_nested_objects(tmp_path: Path) -> None:
    path = tmp_path / "mapping.yaml"
    path.write_text(_mapping_yaml() + "\n")
    mapping = load_mapping_file(path)
    assert mapping.source_name == "homegrown_agent"
    assert mapping.kind_map["tool"] is FragmentKind.TOOL_CALL
    assert mapping.stack_tier_default is StackTier.WITHIN_STACK


def test_invalid_fragment_kind_reports_specific_error(tmp_path: Path) -> None:
    path = tmp_path / "mapping.yaml"
    path.write_text(_mapping_yaml().replace("agent_message", "message_thinking", 1) + "\n")
    with pytest.raises(
        ValueError, match="kind_map contains invalid FragmentKind 'message_thinking'"
    ):
        load_mapping_file(path)


def test_field_path_navigation_supports_nested_dicts() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    fragments = records_to_fragments([_records()[0]], mapping)
    assert fragments[0].actor_id == "main"


def test_field_path_navigation_supports_array_indexes(tmp_path: Path) -> None:
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(_mapping_yaml().replace("metadata.actor.id", "actors.0.id") + "\n")
    record = _records()[0] | {"actors": [{"id": "array_actor"}]}
    record.pop("metadata")
    fragments = records_to_fragments([record], load_mapping_file(mapping))
    assert fragments[0].actor_id == "array_actor"


def test_skip_kinds_drop_records() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    fragments = records_to_fragments(_records(), mapping)
    assert all(fragment.fragment_id != "e6" for fragment in fragments)


def test_followup_absorbs_tool_result_into_parent_tool_call() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    fragments = records_to_fragments(_records(), mapping)
    tool = next(fragment for fragment in fragments if fragment.fragment_id == "e3")
    assert tool.payload["result"] == {"ok": True}


def test_state_mutation_predicate_emits_paired_fragment() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    fragments = records_to_fragments(_records(), mapping)
    state = next(fragment for fragment in fragments if fragment.kind is FragmentKind.STATE_MUTATION)
    assert state.payload["tool_name"] == "write_report"


def test_stack_tier_field_overrides_default() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    fragments = records_to_fragments(_records(), mapping)
    tool = next(fragment for fragment in fragments if fragment.fragment_id == "e3")
    assert tool.stack_tier is StackTier.CROSS_STACK


def test_auto_architecture_detects_human_in_the_loop() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    manifest = records_to_manifest(_records(), mapping, "generic_demo")
    assert manifest["architecture"] == "human_in_the_loop"


def test_auto_architecture_detects_multi_agent_without_human() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    records = [record for record in _records() if record["kind"] != "human_decision"]
    records[0]["metadata"] = {"actor": {"id": "agent-a"}}
    records[1]["metadata"] = {"actor": {"id": "agent-b"}}
    manifest = records_to_manifest(records, mapping, "generic_demo")
    assert manifest["architecture"] == "multi_agent"


def test_synthetic_fragment_id_when_missing() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    record = _records()[0].copy()
    record.pop("id")
    fragments = records_to_fragments([record], mapping)
    assert fragments[0].fragment_id == "generic_jsonl_line_000001"


def test_redact_fields_replace_nested_payload_values() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    record = _records()[2] | {"secrets": {"token": "abc123"}}
    fragments = records_to_fragments(
        [record],
        mapping,
        GenericJsonlIngestOptions(redact_fields=("secrets.token",)),
    )
    assert fragments[0].payload["secrets"]["token"] == "[REDACTED]"


def test_stream_loader_handles_large_jsonl_inputs(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    line = json.dumps(_records()[0])
    path.write_text("\n".join(line for _ in range(10_000)) + "\n")
    records = load_records_file(path)
    assert len(records) == 10_000


def test_determinism_same_input_same_output() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    left = [fragment.to_dict() for fragment in records_to_fragments(_records(), mapping)]
    right = [fragment.to_dict() for fragment in records_to_fragments(_records(), mapping)]
    assert left == right


def test_manifest_round_trip_reconstructs_fragments() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    manifest = records_to_manifest(_records(), mapping, "generic_demo")
    fragments = [Fragment.from_dict(item) for item in manifest["fragments"]]
    assert manifest["stack_tier"] == "within_stack"
    assert fragments[0].parent_trace_id == "homegrown_agent"


def test_timestamp_parsing_accepts_epoch_and_iso() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    fragments = records_to_fragments(_records()[:3], mapping)
    assert fragments[0].timestamp == 1735689600.0
    assert fragments[1].timestamp == 1735689601.0
    assert fragments[2].timestamp == 1735689602.0


def test_validation_reports_missing_timestamp_with_line_number() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    issues = validate_mapping_sample(mapping, [(42, {"id": "x", "kind": "prompt"})])
    assert "timestamp field 'ts' is missing in record at line 42." in issues


def test_validation_reports_unmapped_kind() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    issues = validate_mapping_sample(mapping, [(3, {"id": "x", "ts": 1.0, "kind": "mystery"})])
    assert "record at line 3 has unmapped kind 'mystery'." in issues


def test_strict_unknown_kinds_fail_loud() -> None:
    mapping = load_mapping_file(_write_temp_mapping())
    with pytest.raises(ValueError, match="unmapped kind 'mystery'"):
        records_to_fragments(
            [{"id": "x", "ts": 1.0, "kind": "mystery", "metadata": {"actor": {"id": "main"}}}],
            mapping,
            GenericJsonlIngestOptions(strict_unknown_kinds=True),
        )


def test_iter_jsonl_stream_rejects_non_object_lines() -> None:
    with pytest.raises(TypeError, match="must be an object"):
        iter_jsonl_stream(io.StringIO("[]\n"))


_TEMP_MAPPING_PATH: Path | None = None


def _write_temp_mapping() -> Path:
    global _TEMP_MAPPING_PATH
    if _TEMP_MAPPING_PATH is None:
        path = Path("/tmp/decision_trace_generic_mapping_test.yaml")
        path.write_text(_mapping_yaml() + "\n")
        _TEMP_MAPPING_PATH = path
    return _TEMP_MAPPING_PATH
