"""Dotted-path helpers for Generic JSONL records."""

from __future__ import annotations

from typing import Any

MISSING = object()
NO_DEFAULT = object()


def get_path(data: Any, path: str, default: Any = NO_DEFAULT) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            if not part.isdigit():
                if default is NO_DEFAULT:
                    raise KeyError(f"expected list index in path {path!r}, got {part!r}")
                return default
            idx = int(part)
            if idx >= len(current):
                if default is NO_DEFAULT:
                    raise KeyError(f"index {idx} out of range in path {path!r}")
                return default
            current = current[idx]
            continue
        if not isinstance(current, dict) or part not in current:
            if default is NO_DEFAULT:
                raise KeyError(f"path {path!r} not found")
            return default
        current = current[part]
    return current


def path_exists(data: Any, path: str) -> bool:
    return get_path(data, path, default=MISSING) is not MISSING


def delete_path(data: Any, path: str) -> None:
    current = data
    parts = path.split(".")
    for part in parts[:-1]:
        if isinstance(current, list):
            if not part.isdigit():
                return
            idx = int(part)
            if idx >= len(current):
                return
            current = current[idx]
            continue
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    final = parts[-1]
    if isinstance(current, list):
        if final.isdigit() and int(final) < len(current):
            current.pop(int(final))
        return
    if isinstance(current, dict):
        current.pop(final, None)


def set_path(data: Any, path: str, value: Any) -> None:
    current = data
    parts = path.split(".")
    for part in parts[:-1]:
        if isinstance(current, list):
            if not part.isdigit():
                return
            idx = int(part)
            if idx >= len(current):
                return
            current = current[idx]
            continue
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    final = parts[-1]
    if isinstance(current, list):
        if final.isdigit() and int(final) < len(current):
            current[int(final)] = value
        return
    if isinstance(current, dict):
        current[final] = value


__all__ = [
    "MISSING",
    "delete_path",
    "get_path",
    "path_exists",
    "set_path",
]
