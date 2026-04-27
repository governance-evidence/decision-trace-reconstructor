"""OpenAI Agents trace-to-manifest conversion pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...core.fragment import Fragment
from ...core.manifest import manifest_dict
from .common import OpenAIAgentsIngestOptions
from .events import _merge_trace_group, _normalise_trace
from .fragments import _span_to_fragments


def trace_to_fragments(
    trace: dict[str, Any] | Any,
    opts: OpenAIAgentsIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or OpenAIAgentsIngestOptions()
    normalised = _normalise_trace(trace)
    spans = normalised["spans"]
    span_index = {span["span_id"]: span for span in spans}

    out: list[Fragment] = []
    for span in spans:
        out.extend(_span_to_fragments(span, normalised, span_index, cfg))
    out.sort(key=lambda fragment: (fragment.timestamp, fragment.fragment_id))
    return out


def trace_to_manifest(
    trace: dict[str, Any] | Any,
    scenario_id: str,
    opts: OpenAIAgentsIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or OpenAIAgentsIngestOptions()
    normalised = _normalise_trace(trace)
    fragments = trace_to_fragments(normalised, cfg)
    architecture = _infer_architecture(normalised, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )


def traces_to_manifests(
    traces: Iterable[dict[str, Any] | Any],
    *,
    scenario_id_prefix: str = "openai_agents_ingest",
    opts: OpenAIAgentsIngestOptions | None = None,
    group_into_scenarios: bool = False,
) -> list[dict[str, Any]]:
    cfg = opts or OpenAIAgentsIngestOptions()
    normalised = [_normalise_trace(trace) for trace in traces]
    if not group_into_scenarios:
        return [
            trace_to_manifest(trace, scenario_id=f"{scenario_id_prefix}_{index + 1}", opts=cfg)
            for index, trace in enumerate(normalised)
        ]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for trace in normalised:
        key = str(trace.get("group_id") or trace["trace_id"])
        grouped.setdefault(key, []).append(trace)

    manifests: list[dict[str, Any]] = []
    for index, (group_id, group) in enumerate(sorted(grouped.items())):
        merged = _merge_trace_group(group_id, group)
        manifests.append(
            trace_to_manifest(merged, scenario_id=f"{scenario_id_prefix}_{index + 1}", opts=cfg)
        )
    return manifests


def _infer_architecture(trace: dict[str, Any], opts: OpenAIAgentsIngestOptions) -> str:
    if not opts.auto_architecture:
        return opts.architecture
    spans = trace.get("spans", [])
    if any((span.get("span_data") or {}).get("type") == "handoff" for span in spans):
        return "multi_agent"
    agent_names = {
        str((span.get("span_data") or {}).get("name"))
        for span in spans
        if (span.get("span_data") or {}).get("type") == "agent"
        and (span.get("span_data") or {}).get("name")
    }
    if len(agent_names) >= 2:
        return "multi_agent"
    return opts.architecture
