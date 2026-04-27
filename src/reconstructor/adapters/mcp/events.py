"""MCP transcript loading and normalisation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .common import _to_epoch_seconds

_REDACTED_KEY_PATTERN = re.compile(r"authorization|bearer|api[_-]?key|token", re.IGNORECASE)


def load_transcript_file(path: str | Path) -> list[dict[str, Any]]:
    """Load MCP transcript JSON / JSONL with tolerant line parsing."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_mcp_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    frames: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        parsed = _parse_transcript_line(line)
        if parsed is None:
            continue
        frames.append(_normalise_entry(parsed, index))
    return frames


def find_claude_desktop_logs() -> list[Path]:
    """Locate Claude Desktop MCP transcript logs on common platforms."""
    candidates = [
        Path.home() / "Library" / "Logs" / "Claude",
        Path.home() / ".config" / "Claude" / "logs",
        Path.home() / ".local" / "state" / "Claude" / "logs",
    ]
    matches: list[Path] = []
    for directory in candidates:
        if not directory.exists():
            continue
        matches.extend(sorted(directory.glob("mcp-server-*.log")))
    return matches


def normalise_mcp_input(data: Any) -> list[dict[str, Any]]:
    """Normalise MCP transcript payloads into canonical frame entries."""
    if isinstance(data, list):
        return [_normalise_entry(item, index) for index, item in enumerate(data)]
    if isinstance(data, dict) and "frames" in data and isinstance(data["frames"], list):
        return [_normalise_entry(item, index) for index, item in enumerate(data["frames"])]
    if isinstance(data, dict) and "frame" in data:
        return [_normalise_entry(data, 0)]
    raise ValueError("Unsupported MCP payload: expected transcript entry, list, or {frames:[...]}")


def _normalise_entry(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported MCP transcript entry: {type(data)!r}")
    if "frame" in data:
        frame = _redact_sensitive(data["frame"])
        ts = _to_epoch_seconds(data.get("ts"))
        direction = str(data.get("dir") or "client_to_server")
        transport = str(data.get("transport") or "stdio")
        session_id = str(
            data.get("session_id") or data.get("sessionId") or f"session_{index + 1:04d}"
        )
        return {
            "ts": ts,
            "dir": direction,
            "transport": transport,
            "session_id": session_id,
            "frame": frame,
            "_index": index,
        }
    # Inspector-like fallback: treat the dict itself as the frame.
    frame = _redact_sensitive(data.get("jsonrpc") and data or data.get("message") or data)
    if not isinstance(frame, dict):
        raise ValueError("Unsupported MCP transcript entry: missing frame object")
    return {
        "ts": _to_epoch_seconds(data.get("ts") or data.get("timestamp")),
        "dir": str(data.get("dir") or data.get("direction") or "client_to_server"),
        "transport": str(data.get("transport") or "stdio"),
        "session_id": str(
            data.get("session_id") or data.get("sessionId") or f"session_{index + 1:04d}"
        ),
        "frame": frame,
        "_index": index,
    }


def _parse_transcript_line(line: str) -> dict[str, Any] | None:
    for candidate in (line, line[:-1] if line.endswith(",") else None):
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _REDACTED_KEY_PATTERN.search(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if isinstance(value, str) and ("Bearer " in value or "api_key" in value.lower()):
        return "[REDACTED]"
    return value
