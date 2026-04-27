"""Pydantic AI run loading and normalisation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import _to_epoch_seconds


def load_runs_file(path: str | Path) -> list[dict[str, Any]]:
    """Load Pydantic AI run records from JSON or JSONL."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_pydantic_ai_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    runs: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        runs.extend(normalise_pydantic_ai_input(json.loads(line)))
    return runs


def normalise_pydantic_ai_input(data: Any) -> list[dict[str, Any]]:
    """Normalize supported Pydantic AI offline payloads."""
    if isinstance(data, list):
        return [_normalise_run(item, index) for index, item in enumerate(data)]
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Pydantic AI payload: {type(data)!r}")
    if "runs" in data and isinstance(data["runs"], list):
        return [_normalise_run(item, index) for index, item in enumerate(data["runs"])]
    if "messages" in data:
        return [_normalise_run(data, 0)]
    raise ValueError(
        "Unsupported Pydantic AI payload: expected run dict, list, or {runs:[...]} wrapper"
    )


def _normalise_run(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Pydantic AI run object: {type(data)!r}")
    messages = data.get("messages") or data.get("message_history") or data.get("all_messages") or []
    if not isinstance(messages, list):
        raise TypeError("Pydantic AI run requires a list of messages")
    result_schema = (
        data.get("result_schema") or data.get("resultTypeSchema") or data.get("result_type_schema")
    )
    return {
        "run_id": str(data.get("run_id") or data.get("runId") or f"run_{index + 1:04d}"),
        "agent_name": str(data.get("agent_name") or data.get("agentName") or "pydantic_ai_agent"),
        "model": str(data.get("model") or "unknown_model"),
        "deps_type": data.get("deps_type") or data.get("depsType"),
        "result_type": data.get("result_type") or data.get("resultType"),
        "result_schema": result_schema,
        "tools": _normalise_tools(
            data.get("tools") or data.get("tool_definitions") or data.get("toolDefinitions") or []
        ),
        "messages": [
            _normalise_message(message, message_index)
            for message_index, message in enumerate(messages)
        ],
        "result": data.get("result"),
        "usage": dict(data.get("usage") or {}),
        "ts_start": _to_epoch_seconds(data.get("ts_start") or data.get("tsStart") or 0.0),
        "ts_end": _to_epoch_seconds(
            data.get("ts_end")
            or data.get("tsEnd")
            or data.get("ts_start")
            or data.get("tsStart")
            or 0.0
        ),
    }


def _normalise_tools(tools: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        out.append(
            {
                "tool_name": tool.get("tool_name") or tool.get("name") or "tool_unknown",
                "description": tool.get("description"),
                "params_schema": tool.get("params_schema")
                or tool.get("paramsSchema")
                or tool.get("json_schema"),
                "is_takeover": bool(tool.get("is_takeover") or tool.get("isTakeover")),
            }
        )
    return out


def _normalise_message(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Pydantic AI message object: {type(data)!r}")
    parts = data.get("parts") or []
    if not isinstance(parts, list):
        raise TypeError("Pydantic AI message requires a list of parts")
    return {
        "message_id": str(
            data.get("message_id") or data.get("messageId") or f"msg_{index + 1:04d}"
        ),
        "kind": str(data.get("kind") or "request"),
        "parts": [_normalise_part(part, part_index) for part_index, part in enumerate(parts)],
        "model_name": data.get("model_name") or data.get("modelName"),
        "timestamp": _to_epoch_seconds(data.get("timestamp") or 0.0),
        "kind_metadata": dict(data.get("kind_metadata") or data.get("kindMetadata") or {}),
    }


def _normalise_part(data: Any, index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported Pydantic AI part object: {type(data)!r}")
    return {
        "part_kind": str(data.get("part_kind") or data.get("partKind") or "text"),
        "content": data.get("content"),
        "tool_name": data.get("tool_name") or data.get("toolName"),
        "tool_call_id": data.get("tool_call_id") or data.get("toolCallId"),
        "args": dict(data.get("args") or {}),
        "timestamp": _to_epoch_seconds(data.get("timestamp") or 0.0),
        "_index": index,
    }
