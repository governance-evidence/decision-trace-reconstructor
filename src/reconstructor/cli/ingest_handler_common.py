"""Shared helpers for ingest CLI handlers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..core.fragment import StackTier


def _write_json_payload(payload: dict[str, Any], out: Path) -> None:
    if out == Path("-"):
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n")


def _write_manifest(manifest: dict[str, Any], out: Path) -> None:
    _write_json_payload(manifest, out)
    if out != Path("-"):
        print(f"wrote {out}  ({len(manifest['fragments'])} fragments)")


def _parse_required_stack_tier(value: str) -> StackTier:
    return StackTier(value)


def _parse_optional_stack_tier(value: str | None) -> StackTier | None:
    if value is None:
        return None
    return StackTier(value)


def _comma_tuple(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip() for item in (value or "").split(",") if item.strip())
