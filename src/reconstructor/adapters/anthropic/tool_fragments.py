"""Anthropic tool-use fragment dispatch."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from .common import AnthropicIngestOptions
from .tool_builders import (
    _tool_call_fragment,
    _tool_error_fragment,
    _tool_state_fragment,
)
from .tool_rules import _should_emit_state_mutation, _tool_stack_tier


def _tool_use_fragments(
    round_payload: dict[str, Any],
    actor_id: str,
    results_by_tool_use_id: dict[str, dict[str, Any]],
    opts: AnthropicIngestOptions,
) -> list[Fragment]:
    response = round_payload["response"]
    timestamp = float(round_payload["timestamp"])
    parent_trace_id = str(response.get("id") or round_payload["round_id"])
    out: list[Fragment] = []
    for index, block in enumerate(response.get("content") or []):
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        out.extend(
            _tool_use_fragment_set(
                round_payload,
                actor_id,
                block,
                index,
                results_by_tool_use_id,
                opts,
                timestamp,
                parent_trace_id,
            )
        )
    return out


def _tool_use_fragment_set(
    round_payload: dict[str, Any],
    actor_id: str,
    block: dict[str, Any],
    index: int,
    results_by_tool_use_id: dict[str, dict[str, Any]],
    opts: AnthropicIngestOptions,
    timestamp: float,
    parent_trace_id: str,
) -> list[Fragment]:
    tool_name = str(block.get("name") or "tool")
    tool_use_id = str(block.get("id") or f"tool_{index + 1}")
    result_payload = results_by_tool_use_id.get(tool_use_id)
    tool_timestamp = timestamp + 0.0002 + (index * 0.00001)
    tier = _tool_stack_tier(tool_name, opts)

    out = [
        _tool_call_fragment(
            round_payload,
            actor_id,
            block,
            tool_use_id,
            result_payload,
            tool_timestamp,
            tier,
            parent_trace_id,
        )
    ]
    if _should_emit_state_mutation(tool_name, block.get("input"), opts):
        out.append(
            _tool_state_fragment(
                round_payload,
                actor_id,
                block,
                tool_name,
                tool_use_id,
                tool_timestamp,
                tier,
                parent_trace_id,
            )
        )
    if result_payload is not None and result_payload.get("is_error"):
        out.append(
            _tool_error_fragment(
                round_payload,
                actor_id,
                tool_use_id,
                result_payload,
                tool_timestamp,
                tier,
                parent_trace_id,
            )
        )
    return out


__all__ = ["_tool_use_fragments"]
