"""Generic JSONL followup absorption helpers."""

from __future__ import annotations

from typing import Any

from .common import FollowupRule, GenericJsonlIngestOptions, GenericJsonlMapping
from .paths import MISSING as _MISSING
from .paths import get_path as _get_path
from .payloads import _payload


def _absorb_followup_record(
    record: dict[str, Any],
    raw_kind: str,
    followup_rule: FollowupRule,
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
    parent_lookup: dict[tuple[str, str], dict[str, Any]],
    deferred_followups: dict[tuple[str, str], list[tuple[FollowupRule, Any]]],
) -> None:
    parent_key = _get_path(record, followup_rule.parent_match_field, default=_MISSING)
    if parent_key is _MISSING:
        return
    absorbed_value = _absorbed_value(record, mapping, followup_rule, opts)
    lookup_key = (raw_kind, str(parent_key))
    parent = parent_lookup.get(lookup_key)
    if parent is None:
        deferred_followups.setdefault(lookup_key, []).append((followup_rule, absorbed_value))
        return
    parent["payload"][followup_rule.payload_key] = absorbed_value


def _register_followup_parent(
    fragment: dict[str, Any],
    record: dict[str, Any],
    raw_kind: str,
    mapping: GenericJsonlMapping,
    parent_lookup: dict[tuple[str, str], dict[str, Any]],
    deferred_followups: dict[tuple[str, str], list[tuple[FollowupRule, Any]]],
) -> None:
    for followup_kind, rule in mapping.absorb_followups.items():
        if raw_kind != rule.absorbed_by_kind:
            continue
        pair_value = _get_path(record, rule.pair_match_field, default=_MISSING)
        if pair_value is _MISSING:
            continue
        lookup_key = (followup_kind, str(pair_value))
        parent_lookup[lookup_key] = fragment
        for pending_rule, absorbed_value in deferred_followups.pop(lookup_key, []):
            fragment["payload"][pending_rule.payload_key] = absorbed_value


def _absorbed_value(
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
    rule: FollowupRule,
    opts: GenericJsonlIngestOptions,
) -> Any:
    direct = _get_path(record, rule.payload_key, default=_MISSING)
    if direct is not _MISSING:
        return direct
    payload = _payload(record, mapping, opts)
    if rule.payload_key in payload and len(payload) == 1:
        return payload[rule.payload_key]
    return payload
