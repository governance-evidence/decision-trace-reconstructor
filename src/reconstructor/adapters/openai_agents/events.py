"""OpenAI Agents trace loading and normalisation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import _to_epoch_seconds


def load_traces_file(path: str | Path) -> list[dict[str, Any]]:
    """Load OpenAI Agents traces from JSON / JSONL exports."""
    raw = Path(path).read_text().strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            return normalise_openai_agents_input(json.loads(raw))
        except json.JSONDecodeError:
            pass

    traces: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        traces.extend(normalise_openai_agents_input(json.loads(line)))
    return traces


def normalise_openai_agents_input(data: Any) -> list[dict[str, Any]]:
    """Normalize supported OpenAI Agents trace payloads."""
    if isinstance(data, list):
        return [_normalise_trace(item) for item in data]
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported OpenAI Agents payload: {type(data)!r}")
    if "traces" in data and isinstance(data["traces"], list):
        return [_normalise_trace(item) for item in data["traces"]]
    if "trace_id" in data or "spans" in data:
        return [_normalise_trace(data)]
    raise ValueError(
        "Unsupported OpenAI Agents payload: expected trace dict or {traces:[...]} wrapper"
    )


def _normalise_trace(trace: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(trace, dict):
        raise TypeError(f"Unsupported OpenAI Agents trace object: {type(trace)!r}")
    trace_id = str(trace.get("trace_id") or trace.get("traceId") or "trace_unknown")
    spans = [_normalise_span(span) for span in trace.get("spans", [])]
    spans.sort(key=lambda span: (span["_ts"], span["span_id"]))
    return {
        "trace_id": trace_id,
        "workflow_name": trace.get("workflow_name")
        or trace.get("workflowName")
        or "openai_agents_workflow",
        "group_id": trace.get("group_id") or trace.get("groupId"),
        "metadata": dict(trace.get("metadata") or {}),
        "spans": spans,
    }


def _normalise_span(span: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(span, dict):
        raise TypeError(f"Unsupported OpenAI Agents span object: {type(span)!r}")
    span_data = dict(span.get("span_data") or span.get("spanData") or {})
    return {
        "span_id": str(span.get("span_id") or span.get("spanId") or "span_unknown"),
        "trace_id": str(span.get("trace_id") or span.get("traceId") or "trace_unknown"),
        "parent_id": span.get("parent_id") or span.get("parentId"),
        "started_at": span.get("started_at") or span.get("startedAt"),
        "ended_at": span.get("ended_at") or span.get("endedAt"),
        "span_data": span_data,
        "metadata": dict(span.get("metadata") or {}),
        "error": span.get("error"),
        "_ts": _to_epoch_seconds(span.get("started_at") or span.get("startedAt")),
    }


def _merge_trace_group(group_id: str, traces: list[dict[str, Any]]) -> dict[str, Any]:
    workflow_name = traces[0].get("workflow_name") or "openai_agents_group"
    metadata: dict[str, Any] = {}
    spans: list[dict[str, Any]] = []
    for trace in traces:
        metadata.update(trace.get("metadata") or {})
        spans.extend(trace.get("spans", []))
    spans.sort(key=lambda span: (span["_ts"], span["span_id"]))
    return {
        "trace_id": traces[0]["trace_id"],
        "workflow_name": workflow_name,
        "group_id": group_id,
        "metadata": metadata,
        "spans": spans,
    }
