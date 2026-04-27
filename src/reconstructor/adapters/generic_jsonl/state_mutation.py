"""Generic JSONL state mutation fragment helpers."""

from __future__ import annotations

import re
from typing import Any

from ...core.fragment import FragmentKind
from .common import GenericJsonlMapping
from .paths import MISSING as _MISSING
from .paths import get_path as _get_path


def _should_emit_state_mutation(
    mapped_kind: FragmentKind,
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
) -> bool:
    return mapped_kind is FragmentKind.TOOL_CALL and _state_mutation_matches(record, mapping)


def _state_mutation_fragment(
    parent: dict[str, Any],
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
) -> dict[str, Any]:
    payload = {"tool_name": parent["payload"].get("tool_name")}
    if isinstance(record.get("result"), dict):
        payload["result"] = record["result"]
    return {
        "fragment_id": f"{parent['fragment_id']}_state",
        "timestamp": parent["timestamp"],
        "kind": FragmentKind.STATE_MUTATION.value,
        "stack_tier": parent["stack_tier"],
        "actor_id": parent["actor_id"],
        "payload": payload,
        "parent_trace_id": parent["parent_trace_id"],
        "decision_id_hint": None,
        "_raw_kind": "state_mutation",
    }


def _state_mutation_matches(record: dict[str, Any], mapping: GenericJsonlMapping) -> bool:
    predicate = mapping.state_mutation_predicate
    if predicate is None:
        return False
    value = _get_path(record, predicate.field, default=_MISSING)
    if value is _MISSING:
        return False
    return re.search(predicate.matches_regex, str(value)) is not None
