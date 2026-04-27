"""Compatibility facade for Generic JSONL utility helpers."""

from __future__ import annotations

from .paths import MISSING, delete_path, get_path, path_exists, set_path
from .yaml import parse_simple_yaml

__all__ = [
    "MISSING",
    "delete_path",
    "get_path",
    "parse_simple_yaml",
    "path_exists",
    "set_path",
]
