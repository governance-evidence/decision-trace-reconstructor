"""Anthropic round loading and normalisation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import _to_epoch_seconds


def load_rounds_file(path: str | Path) -> list[dict[str, Any]]:
    """Load Anthropic request/response rounds from JSON or JSONL."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_anthropic_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    rounds: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        rounds.append(_normalise_round(json.loads(line), index))
    return rounds


def normalise_anthropic_input(data: Any) -> list[dict[str, Any]]:
    """Normalise Anthropic offline export payloads."""
    if isinstance(data, list):
        return [_normalise_round(item, index) for index, item in enumerate(data)]
    if isinstance(data, dict) and {"request", "response"}.issubset(data):
        return [_normalise_round(data, 0)]
    if isinstance(data, dict) and "rounds" in data and isinstance(data["rounds"], list):
        return [_normalise_round(item, index) for index, item in enumerate(data["rounds"])]
    raise ValueError(
        "Unsupported Anthropic payload: expected {request,response} round, list, or {rounds:[...]}"
    )


def _normalise_round(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Anthropic round object: {type(data)!r}")
    request = dict(data.get("request") or {})
    response = dict(data.get("response") or {})
    if not request or not response:
        raise ValueError("Anthropic round requires non-empty request and response objects")
    return {
        "round_id": str(data.get("round_id") or data.get("roundId") or f"round_{index + 1:04d}"),
        "timestamp": _to_epoch_seconds(data.get("timestamp")),
        "request": request,
        "response": response,
    }
