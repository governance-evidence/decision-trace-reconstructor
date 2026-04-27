"""Edge-case contracts for the Generic JSONL adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reconstructor.adapters.generic_jsonl import (
    GenericJsonlIngestOptions,
    load_mapping_file,
    records_to_fragments,
    records_to_manifest,
)
from reconstructor.adapters.generic_jsonl.paths import delete_path, get_path, path_exists, set_path
from reconstructor.core.fragment import FragmentKind, StackTier


def _mapping_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "source_name": "edge_agent",
        "fields": {
            "fragment_id": "id",
            "timestamp": "ts",
            "actor_id": "actor.id",
            "payload": None,
        },
        "kind_field": "kind",
        "kind_map": {
            "prompt": "agent_message",
            "tool": "tool_call",
            "tool_result": "agent_message",
            "human": "human_approval",
        },
        "skip_kinds": ["", "debug"],
        "state_mutation_predicate": {"field": "tool", "matches_regex": "write|delete"},
        "absorb_followups": {
            "tool_result": {
                "absorbed_by_kind": "tool",
                "payload_key": "result",
                "pair_match_field": "id",
                "parent_match_field": "parent_id",
            }
        },
        "stack_tier_field": "tier",
        "stack_tier_default": "within_stack",
        "architecture": "auto",
    }


def _write_mapping(tmp_path: Path, data: dict[str, object] | None = None) -> Path:
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(data or _mapping_dict()))
    return path


def test_empty_mapping_file_fails_loud(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("\n")

    with pytest.raises(ValueError, match="mapping file is empty"):
        load_mapping_file(path)


def test_mapping_validation_errors_are_operator_facing(tmp_path: Path) -> None:
    bad_schema = _mapping_dict() | {"schema_version": "2.0"}
    with pytest.raises(ValueError, match="unknown schema_version '2.0'"):
        load_mapping_file(_write_mapping(tmp_path, bad_schema))

    missing_fields = dict(_mapping_dict())
    missing_fields.pop("fields")
    with pytest.raises(ValueError, match="requires a 'fields' object"):
        load_mapping_file(_write_mapping(tmp_path, missing_fields))

    empty_kind_map = _mapping_dict() | {"kind_map": {}}
    with pytest.raises(ValueError, match="requires a non-empty kind_map"):
        load_mapping_file(_write_mapping(tmp_path, empty_kind_map))


def test_payload_path_scalar_is_wrapped_and_actor_override_wins(tmp_path: Path) -> None:
    mapping_data = _mapping_dict()
    mapping_data["fields"] = {
        "fragment_id": "id",
        "timestamp": "ts",
        "actor_id": "actor.id",
        "payload": "message.text",
    }
    mapping = load_mapping_file(_write_mapping(tmp_path, mapping_data))

    fragments = records_to_fragments(
        [
            {
                "id": "e1",
                "ts": 1.0,
                "kind": "prompt",
                "actor": {"id": "original"},
                "message": {"text": "hello"},
            }
        ],
        mapping,
        GenericJsonlIngestOptions(actor_override="override_actor"),
    )

    assert fragments[0].actor_id == "override_actor"
    assert fragments[0].payload == {"value": "hello"}


def test_deferred_followup_absorbs_result_seen_before_parent(tmp_path: Path) -> None:
    mapping = load_mapping_file(_write_mapping(tmp_path))
    records = [
        {
            "id": "result-1",
            "parent_id": "tool-1",
            "ts": 2.0,
            "kind": "tool_result",
            "result": {"ok": True},
            "actor": {"id": "agent"},
        },
        {
            "id": "tool-1",
            "ts": 1.0,
            "kind": "tool",
            "tool": "read_report",
            "actor": {"id": "agent"},
        },
    ]

    fragments = records_to_fragments(records, mapping)

    assert len(fragments) == 1
    assert fragments[0].fragment_id == "tool-1"
    assert fragments[0].payload["result"] == {"ok": True}


def test_state_mutation_predicate_missing_field_does_not_emit_state(tmp_path: Path) -> None:
    mapping = load_mapping_file(_write_mapping(tmp_path))

    fragments = records_to_fragments(
        [{"id": "tool-1", "ts": 1.0, "kind": "tool", "actor": {"id": "agent"}}],
        mapping,
    )

    assert [fragment.kind for fragment in fragments] == [FragmentKind.TOOL_CALL]


def test_manifest_options_override_mapping_architecture_and_stack_tier(tmp_path: Path) -> None:
    mapping = load_mapping_file(_write_mapping(tmp_path))

    manifest = records_to_manifest(
        [{"id": "e1", "ts": 1.0, "kind": "prompt", "actor": {"id": "agent"}}],
        mapping,
        "override_case",
        GenericJsonlIngestOptions(
            architecture="multi_agent",
            stack_tier=StackTier.CROSS_STACK,
        ),
    )

    assert manifest["architecture"] == "multi_agent"
    assert manifest["stack_tier"] == "cross_stack"
    assert manifest["fragments"][0]["stack_tier"] == "cross_stack"


def test_invalid_record_stack_tier_is_rejected(tmp_path: Path) -> None:
    mapping = load_mapping_file(_write_mapping(tmp_path))

    with pytest.raises(ValueError, match="bad_tier"):
        records_to_fragments(
            [
                {
                    "id": "e1",
                    "ts": 1.0,
                    "kind": "prompt",
                    "tier": "bad_tier",
                    "actor": {"id": "agent"},
                }
            ],
            mapping,
        )


def test_path_helpers_return_defaults_and_ignore_invalid_mutations() -> None:
    data = {"items": [{"name": "first"}], "value": 1}

    assert get_path(data, "items.bad.name", default="fallback") == "fallback"
    assert get_path(data, "items.99.name", default="fallback") == "fallback"
    assert get_path(data, "missing.path", default="fallback") == "fallback"
    assert not path_exists(data, "items.99.name")

    set_path(data, "value.name", "ignored")
    set_path(data, "items.99.name", "ignored")
    delete_path(data, "value.name")
    delete_path(data, "items.bad.name")

    assert data == {"items": [{"name": "first"}], "value": 1}
