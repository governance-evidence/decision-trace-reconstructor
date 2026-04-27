"""OTLP timestamp and trace identifier normalization helpers."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any


def to_unix_seconds(value: Any) -> float:
    return _to_unix_nano(value) / 1_000_000_000


def _to_unix_nano(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value > 1_000_000_000_000:
            return int(value)
        return int(value * 1_000_000_000)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return int(
            datetime.fromisoformat(stripped.replace("Z", "+00:00")).timestamp() * 1_000_000_000
        )
    if isinstance(value, datetime):
        return int(value.timestamp() * 1_000_000_000)
    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")


def _norm_trace_like_id(value: Any, *, expected_bytes: int) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    lowered = raw.lower()
    if len(lowered) == expected_bytes * 2 and all(ch in "0123456789abcdef" for ch in lowered):
        return lowered
    try:
        decoded = base64.b64decode(raw, validate=True)
    except Exception:
        return lowered
    if len(decoded) == expected_bytes:
        return decoded.hex()
    return lowered


def _norm_parent_id(value: Any) -> str | None:
    raw = str(value or "")
    if not raw:
        return None
    norm = _norm_trace_like_id(raw, expected_bytes=8)
    return norm or None
