"""Generic JSONL record kind resolution helpers."""

from __future__ import annotations

import json
from typing import Any

from ...core.fragment import FragmentKind
from .common import GenericJsonlIngestOptions, GenericJsonlMapping
from .paths import MISSING as _MISSING
from .paths import get_path as _get_path


def _record_raw_kind(
    line_no: int,
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
) -> str:
    raw_kind_value = _get_path(record, mapping.kind_field, default=_MISSING)
    if raw_kind_value is _MISSING:
        raise ValueError(
            f"kind field {mapping.kind_field!r} is missing in record at line {line_no}"
        )
    return str(raw_kind_value)


def _mapped_kind_for_record(
    raw_kind: str,
    line_no: int,
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
) -> FragmentKind | None:
    mapped_kind = mapping.kind_map.get(raw_kind)
    if mapped_kind is None and opts.strict_unknown_kinds:
        raise ValueError(f"record at line {line_no} has unmapped kind {raw_kind!r}")
    return mapped_kind


def _resolve_human_kind(kind: FragmentKind, payload: dict[str, Any]) -> FragmentKind:
    if kind is not FragmentKind.HUMAN_APPROVAL:
        return kind
    raw = json.dumps(payload, sort_keys=True).lower()
    if any(token in raw for token in ("rejected", "reject", "denied", "deny")):
        return FragmentKind.HUMAN_REJECTION
    return FragmentKind.HUMAN_APPROVAL
