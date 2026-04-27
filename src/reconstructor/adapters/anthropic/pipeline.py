"""Anthropic round-to-manifest conversion pipeline."""

from __future__ import annotations

import hashlib
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from ...core.manifest import manifest_dict
from .common import AnthropicIngestOptions
from .events import _normalise_round
from .fragments import (
    _actor_id,
    _fragment,
    _request_message_fragments,
    _request_snapshot_fragment,
    _response_message_fragments,
    _response_model_fragments,
    _tool_use_fragments,
)


def rounds_to_fragments(
    rounds: list[dict[str, Any]] | Any,
    opts: AnthropicIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or AnthropicIngestOptions()
    normalised = [
        _normalise_round(round_payload, index)
        for index, round_payload in enumerate(rounds if isinstance(rounds, list) else [rounds])
    ]
    results_by_tool_use_id = _collect_tool_results(normalised)
    out: list[Fragment] = []
    for round_payload in normalised:
        out.extend(_round_to_fragments(round_payload, results_by_tool_use_id, cfg))
    out.sort(key=lambda fragment: (fragment.timestamp, fragment.fragment_id))
    return out


def rounds_to_manifest(
    rounds: list[dict[str, Any]] | Any,
    scenario_id: str,
    opts: AnthropicIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or AnthropicIngestOptions()
    fragments = rounds_to_fragments(rounds, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=cfg.architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )


def _round_to_fragments(
    round_payload: dict[str, Any],
    results_by_tool_use_id: dict[str, dict[str, Any]],
    opts: AnthropicIngestOptions,
) -> list[Fragment]:
    request = round_payload["request"]
    response = round_payload["response"]
    timestamp = float(round_payload["timestamp"])
    actor_id = _actor_id(request, response, opts)
    parent_trace_id = str(response.get("id") or round_payload["round_id"])
    decision_id_hint = parent_trace_id
    out: list[Fragment] = []

    out.append(_request_snapshot_fragment(round_payload, actor_id, opts))
    out.extend(_request_message_fragments(round_payload, actor_id, opts))
    out.extend(_response_model_fragments(round_payload, actor_id, opts))
    out.extend(_response_message_fragments(round_payload, actor_id, opts))
    out.extend(_tool_use_fragments(round_payload, actor_id, results_by_tool_use_id, opts))

    metadata = request.get("metadata") or {}
    human_decision = metadata.get("demm_human_approval")
    if human_decision == "approved":
        out.append(
            _fragment(
                f"anthropic_{round_payload['round_id']}_human_approval",
                FragmentKind.HUMAN_APPROVAL,
                timestamp=timestamp + 0.0002,
                stack_tier=StackTier.HUMAN,
                actor_id=actor_id,
                parent_trace_id=parent_trace_id,
                decision_id_hint=decision_id_hint,
                payload={"decision": "approved"},
            )
        )
    elif human_decision == "rejected":
        out.append(
            _fragment(
                f"anthropic_{round_payload['round_id']}_human_rejection",
                FragmentKind.HUMAN_REJECTION,
                timestamp=timestamp + 0.0002,
                stack_tier=StackTier.HUMAN,
                actor_id=actor_id,
                parent_trace_id=parent_trace_id,
                decision_id_hint=decision_id_hint,
                payload={"decision": "rejected"},
            )
        )
    return out


def _collect_tool_results(rounds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for round_payload in rounds:
        for message in round_payload["request"].get("messages") or []:
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_use_id = block.get("tool_use_id")
                if not tool_use_id:
                    continue
                out[str(tool_use_id)] = {
                    "result": _sanitise_tool_result(block.get("content")),
                    "is_error": bool(block.get("is_error")),
                }
    return out


def _sanitise_tool_result(content: Any) -> Any:
    if isinstance(content, list):
        return [_sanitise_tool_result(item) for item in content]
    if isinstance(content, dict):
        if content.get("type") == "image":
            source = content.get("source") or {}
            data = str(source.get("data") or "")
            return {
                "type": "image",
                "sha256": hashlib.sha256(data.encode("utf-8")).hexdigest(),
                "length": len(data),
                "media_type": source.get("media_type"),
                **({"width": source.get("width")} if source.get("width") is not None else {}),
                **({"height": source.get("height")} if source.get("height") is not None else {}),
            }
        return {key: _sanitise_tool_result(value) for key, value in content.items()}
    return content
