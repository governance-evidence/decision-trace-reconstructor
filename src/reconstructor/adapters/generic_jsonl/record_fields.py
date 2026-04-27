"""Generic JSONL record field resolution helpers."""

from __future__ import annotations

from typing import Any

from ...core.fragment import StackTier
from .common import GenericJsonlIngestOptions, GenericJsonlMapping
from .paths import MISSING as _MISSING
from .paths import get_path as _get_path


def _fragment_id(record: dict[str, Any], mapping: GenericJsonlMapping, line_no: int) -> str:
    if mapping.fields.fragment_id is not None:
        value = _get_path(record, mapping.fields.fragment_id, default=_MISSING)
        if value is not _MISSING and value not in (None, ""):
            return str(value)
    return f"generic_jsonl_line_{line_no:06d}"


def _actor_id(
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
    fragment_id: str,
) -> str:
    if opts.actor_override is not None:
        return opts.actor_override
    if mapping.fields.actor_id is not None:
        value = _get_path(record, mapping.fields.actor_id, default=_MISSING)
        if value is not _MISSING and value not in (None, ""):
            return str(value)
    return f"agent_{fragment_id[:8]}"


def _record_stack_tier(
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
) -> StackTier:
    if mapping.stack_tier_field is not None:
        value = _get_path(record, mapping.stack_tier_field, default=_MISSING)
        if value is not _MISSING and value not in (None, ""):
            return StackTier(str(value))
    return opts.stack_tier or mapping.stack_tier_default


def _mapped_field_paths(mapping: GenericJsonlMapping) -> tuple[str, ...]:
    paths = [mapping.kind_field, mapping.fields.timestamp]
    for value in (mapping.fields.fragment_id, mapping.fields.actor_id, mapping.stack_tier_field):
        if value is not None:
            paths.append(value)
    return tuple(paths)
