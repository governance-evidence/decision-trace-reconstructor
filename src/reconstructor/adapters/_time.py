"""Shared timestamp coercion helpers for adapter normalization layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_MS_EPOCH_THRESHOLD = 10_000_000_000


def _scaled(numeric: float, ms_heuristic: bool) -> float:
    if ms_heuristic and numeric > _MS_EPOCH_THRESHOLD:
        return numeric / 1000.0
    return numeric


def to_epoch_seconds(value: Any, *, ms_heuristic: bool = False) -> float:
    """Coerce None / numeric / datetime / ISO-8601 string to Unix-epoch seconds.

    With *ms_heuristic*, numeric values above 10_000_000_000 are treated as
    milliseconds and scaled to seconds.
    """
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return _scaled(float(value), ms_heuristic)
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0.0
        if stripped.isdigit():
            return _scaled(float(stripped), ms_heuristic)
        return datetime.fromisoformat(stripped.replace("Z", "+00:00")).timestamp()
    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")


def to_epoch_seconds_lenient(value: Any, *, label: str) -> float:
    """Coerce numeric / numeric-string / ISO-8601 string to Unix-epoch seconds.

    Unlike :func:`to_epoch_seconds`, plain float strings are accepted and
    datetime objects are not.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    raise TypeError(f"Unsupported {label} timestamp: {type(value)!r}")
