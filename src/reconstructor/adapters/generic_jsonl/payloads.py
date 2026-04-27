"""Generic JSONL payload extraction and redaction helpers."""

from __future__ import annotations

import json
from typing import Any

from .common import GenericJsonlIngestOptions, GenericJsonlMapping
from .paths import delete_path as _delete_path
from .paths import get_path as _get_path
from .paths import set_path as _set_path
from .record_fields import _mapped_field_paths


def _payload(
    record: dict[str, Any],
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
) -> dict[str, Any]:
    payload_record = json.loads(json.dumps(record))
    if mapping.fields.payload is not None:
        payload_value = _get_path(payload_record, mapping.fields.payload, default={})
        payload = payload_value if isinstance(payload_value, dict) else {"value": payload_value}
    else:
        for path in _mapped_field_paths(mapping):
            _delete_path(payload_record, path)
        payload = payload_record
    for redact_path in opts.redact_fields:
        _set_path(payload, redact_path, "[REDACTED]")
    return payload if isinstance(payload, dict) else {"value": payload}
