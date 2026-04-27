"""Shared Generic JSONL adapter types and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

from ...core.fragment import FragmentKind, StackTier

_VALID_ARCHITECTURES = {"single_agent", "multi_agent", "human_in_the_loop", "auto"}


@dataclass(frozen=True)
class MappingFields:
    timestamp: str
    fragment_id: str | None = None
    actor_id: str | None = None
    payload: str | None = None


@dataclass(frozen=True)
class StateMutationPredicate:
    field: str
    matches_regex: str


@dataclass(frozen=True)
class FollowupRule:
    absorbed_by_kind: str
    payload_key: str
    pair_match_field: str
    parent_match_field: str


@dataclass(frozen=True)
class GenericJsonlMapping:
    schema_version: str
    source_name: str
    fields: MappingFields
    kind_field: str
    kind_map: dict[str, FragmentKind]
    skip_kinds: tuple[str, ...] = ()
    state_mutation_predicate: StateMutationPredicate | None = None
    absorb_followups: dict[str, FollowupRule] = field(default_factory=dict)
    stack_tier_field: str | None = None
    stack_tier_default: StackTier = StackTier.WITHIN_STACK
    architecture: str = "single_agent"


@dataclass(frozen=True)
class GenericJsonlIngestOptions:
    architecture: str | None = None
    stack_tier: StackTier | None = None
    strict_unknown_kinds: bool = False
    redact_fields: tuple[str, ...] = ()
    actor_override: str | None = None


def _coerce_records(
    records: list[tuple[int, dict[str, Any]]] | list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    out: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(records, start=1):
        if isinstance(item, tuple):
            line_no, record = item
            out.append((line_no, cast(dict[str, Any], record)))
        else:
            out.append((index, cast(dict[str, Any], item)))
    return out


def _to_epoch_seconds(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text).timestamp()
        except ValueError:
            return float(value)
    raise TypeError(f"Unsupported timestamp value: {value!r}")
