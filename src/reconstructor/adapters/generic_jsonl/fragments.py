"""Generic JSONL record-to-fragment mapping orchestration."""

from __future__ import annotations

from typing import Any

from .common import FollowupRule, GenericJsonlIngestOptions, GenericJsonlMapping
from .followups import _absorb_followup_record, _register_followup_parent
from .record_fragments import (
    _mapped_kind_for_record,
    _record_raw_kind,
    _record_to_fragment_dict,
    _should_emit_state_mutation,
    _state_mutation_fragment,
)


def _records_to_fragment_dicts(
    records: list[tuple[int, dict[str, Any]]],
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
) -> list[dict[str, Any]]:
    fragments: list[dict[str, Any]] = []
    parent_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    deferred_followups: dict[tuple[str, str], list[tuple[FollowupRule, Any]]] = {}

    for line_no, record in records:
        raw_kind = _record_raw_kind(line_no, record, mapping)
        if raw_kind in mapping.skip_kinds:
            continue

        followup_rule = mapping.absorb_followups.get(raw_kind)
        if followup_rule is not None:
            _absorb_followup_record(
                record,
                raw_kind,
                followup_rule,
                mapping,
                opts,
                parent_lookup,
                deferred_followups,
            )
            continue

        mapped_kind = _mapped_kind_for_record(raw_kind, line_no, mapping, opts)
        if mapped_kind is None:
            continue

        fragment = _record_to_fragment_dict(line_no, record, raw_kind, mapped_kind, mapping, opts)
        fragments.append(fragment)
        _register_followup_parent(
            fragment,
            record,
            raw_kind,
            mapping,
            parent_lookup,
            deferred_followups,
        )
        if _should_emit_state_mutation(mapped_kind, record, mapping):
            fragments.append(_state_mutation_fragment(fragment, record, mapping))

    return fragments


def _serialise_fragment_dict(fragment: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fragment.items() if not key.startswith("_")}
