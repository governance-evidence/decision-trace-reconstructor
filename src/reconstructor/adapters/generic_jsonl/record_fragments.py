"""Generic JSONL single-record fragment conversion helpers."""

from __future__ import annotations

from typing import Any

from ...core.fragment import FragmentKind
from .common import (
    GenericJsonlIngestOptions,
    GenericJsonlMapping,
    _to_epoch_seconds,
)
from .paths import MISSING as _MISSING
from .paths import get_path as _get_path
from .payloads import _payload
from .record_fields import _actor_id, _fragment_id, _record_stack_tier
from .record_kind import (
    _mapped_kind_for_record,
    _record_raw_kind,
    _resolve_human_kind,
)
from .state_mutation import (
    _should_emit_state_mutation,
    _state_mutation_fragment,
)


def _record_to_fragment_dict(
    line_no: int,
    record: dict[str, Any],
    raw_kind: str,
    mapped_kind: FragmentKind,
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
) -> dict[str, Any]:
    fragment_id = _fragment_id(record, mapping, line_no)
    timestamp_value = _get_path(record, mapping.fields.timestamp, default=_MISSING)
    if timestamp_value is _MISSING:
        raise ValueError(
            f"timestamp field {mapping.fields.timestamp!r} is missing in record at line {line_no}"
        )
    actor_id = _actor_id(record, mapping, opts, fragment_id)
    payload = _payload(record, mapping, opts)
    resolved_kind = _resolve_human_kind(mapped_kind, payload)
    if resolved_kind is FragmentKind.TOOL_CALL and "tool_name" not in payload:
        tool_name = record.get("tool") or record.get("tool_name") or record.get("name")
        if tool_name is not None:
            payload["tool_name"] = str(tool_name)
    tier = _record_stack_tier(record, mapping, opts)
    return {
        "fragment_id": fragment_id,
        "timestamp": _to_epoch_seconds(timestamp_value),
        "kind": resolved_kind.value,
        "stack_tier": tier.value,
        "actor_id": actor_id,
        "payload": payload,
        "parent_trace_id": mapping.source_name,
        "decision_id_hint": None,
        "_raw_kind": raw_kind,
    }


__all__ = [
    "_mapped_kind_for_record",
    "_record_raw_kind",
    "_record_to_fragment_dict",
    "_should_emit_state_mutation",
    "_state_mutation_fragment",
]
