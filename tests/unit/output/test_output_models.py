"""Pydantic model round-trip tests for the four canonical result artifacts.

Goal: any change to ``models.py`` that breaks wire-format compatibility with
the committed ``results/*.json`` baselines must fail this test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reconstructor.output.models import (
    CellResults,
    GenericJsonlMappingConfig,
    NamedIncidentResults,
    PerPropertyTable,
    PerScenarioResults,
)

RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"


@pytest.mark.parametrize(
    "filename, model_cls",
    [
        ("cells.json", CellResults),
        ("per_property.json", PerPropertyTable),
        ("per_scenario.json", PerScenarioResults),
        ("named_incidents.json", NamedIncidentResults),
    ],
)
def test_results_round_trip_through_pydantic(filename: str, model_cls: type) -> None:
    """Each result file parses cleanly and re-emits identical JSON."""
    raw = json.loads((RESULTS_DIR / filename).read_text())
    parsed = model_cls.model_validate(raw)
    assert parsed.model_dump(mode="json") == raw


def test_json_schema_export_is_stable() -> None:
    """Each root model produces a valid JSON Schema document."""
    for model_cls in (
        CellResults,
        GenericJsonlMappingConfig,
        PerPropertyTable,
        PerScenarioResults,
        NamedIncidentResults,
    ):
        schema = model_cls.model_json_schema()
        # Pydantic v2 emits draft-2020-12 style; minimal sanity checks.
        assert isinstance(schema, dict)
        assert "type" in schema or "$defs" in schema or "$ref" in schema


def test_generic_jsonl_mapping_config_validates_example_mapping() -> None:
    raw = {
        "schema_version": "1.0",
        "source_name": "homegrown_agent",
        "fields": {
            "fragment_id": "id",
            "timestamp": "ts",
            "actor_id": "metadata.actor.id",
            "payload": None,
        },
        "kind_field": "kind",
        "kind_map": {
            "prompt": "agent_message",
            "llm": "model_generation",
            "tool": "tool_call",
        },
        "skip_kinds": ["heartbeat"],
        "state_mutation_predicate": {
            "field": "tool",
            "matches_regex": "write_.*",
        },
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

    parsed = GenericJsonlMappingConfig.model_validate(raw)
    assert parsed.model_dump(mode="json") == raw
