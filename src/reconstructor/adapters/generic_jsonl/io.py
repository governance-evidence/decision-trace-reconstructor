"""Generic JSONL mapping and record file IO."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from .common import GenericJsonlMapping
from .mapping import _normalise_mapping
from .yaml import parse_simple_yaml as _parse_simple_yaml


def load_mapping_file(path: str | Path) -> GenericJsonlMapping:
    raw = Path(path).read_text().strip()
    if not raw:
        raise ValueError("mapping file is empty")
    if raw[0] in "[{":
        data = json.loads(raw)
    else:
        data = _parse_simple_yaml(raw)
    return _normalise_mapping(data)


def iter_records_file(path: str | Path) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    with Path(path).open() as handle:
        records.extend(iter_jsonl_stream(handle))
    return records


def iter_jsonl_stream(handle: TextIO) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    for line_no, raw_line in enumerate(handle, start=1):
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise TypeError(f"JSONL record at line {line_no} must be an object")
        records.append((line_no, data))
    return records


def load_records_file(path: str | Path) -> list[dict[str, Any]]:
    return [record for _, record in iter_records_file(path)]
