"""Generic JSONL mapping validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import GenericJsonlMapping, _coerce_records
from .io import iter_records_file, load_mapping_file
from .paths import MISSING as _MISSING
from .paths import get_path as _get_path
from .paths import path_exists as _path_exists


def validate_mapping_file(mapping_path: str | Path, sample_path: str | Path) -> list[str]:
    mapping = load_mapping_file(mapping_path)
    sample = iter_records_file(sample_path)[:100]
    return validate_mapping_sample(mapping, sample)


def validate_mapping_sample(
    mapping: GenericJsonlMapping,
    sample_records: list[tuple[int, dict[str, Any]]] | list[dict[str, Any]],
) -> list[str]:
    records = _coerce_records(sample_records)
    issues: list[str] = []

    for path, label in _configured_paths(mapping):
        if not any(_path_exists(record, path) for _, record in records):
            issues.append(
                f"field path {path!r} not found in any record (sampled first {len(records)} records)."
            )
        if label == "timestamp":
            for line_no, record in records:
                if not _path_exists(record, path):
                    raw_kind = _get_path(record, mapping.kind_field, default=None)
                    if raw_kind in mapping.skip_kinds:
                        continue
                    issues.append(
                        f"timestamp field {path!r} is missing in record at line {line_no}."
                    )
                    break
    for line_no, record in records:
        raw_kind = _get_path(record, mapping.kind_field, default=_MISSING)
        if raw_kind is _MISSING:
            issues.append(
                f"kind field {mapping.kind_field!r} is missing in record at line {line_no}."
            )
            continue
        if str(raw_kind) in mapping.skip_kinds:
            continue
        if str(raw_kind) not in mapping.kind_map and str(raw_kind) not in mapping.absorb_followups:
            issues.append(f"record at line {line_no} has unmapped kind {raw_kind!r}.")
    return issues


def _configured_paths(mapping: GenericJsonlMapping) -> list[tuple[str, str]]:
    paths = [(mapping.fields.timestamp, "timestamp"), (mapping.kind_field, "kind_field")]
    if mapping.fields.fragment_id is not None:
        paths.append((mapping.fields.fragment_id, "fragment_id"))
    if mapping.fields.actor_id is not None:
        paths.append((mapping.fields.actor_id, "actor_id"))
    if mapping.stack_tier_field is not None:
        paths.append((mapping.stack_tier_field, "stack_tier_field"))
    if mapping.state_mutation_predicate is not None:
        paths.append((mapping.state_mutation_predicate.field, "state_mutation_predicate"))
    for _, rule in mapping.absorb_followups.items():
        paths.append((rule.pair_match_field, "absorb_pair_match_field"))
        paths.append((rule.parent_match_field, "absorb_parent_match_field"))
    return paths
