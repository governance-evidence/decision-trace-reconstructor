"""Anthropic response fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import AnthropicIngestOptions
from .fragment_common import _fragment
from .message_payloads import _thinking_payload


def _response_model_fragments(
    round_payload: dict[str, Any],
    actor_id: str,
    opts: AnthropicIngestOptions,
) -> list[Fragment]:
    response = round_payload["response"]
    timestamp = float(round_payload["timestamp"])
    parent_trace_id = str(response.get("id") or round_payload["round_id"])
    usage = dict(response.get("usage") or {})
    token_count = None
    if isinstance(usage.get("input_tokens"), int) and isinstance(usage.get("output_tokens"), int):
        token_count = usage["input_tokens"] + usage["output_tokens"]

    out = [
        _fragment(
            f"anthropic_{round_payload['round_id']}_response_model",
            FragmentKind.MODEL_GENERATION,
            timestamp=timestamp + 0.00005,
            stack_tier=opts.stack_tier,
            actor_id=actor_id,
            parent_trace_id=parent_trace_id,
            decision_id_hint=parent_trace_id,
            payload={
                "model_id": response.get("model") or round_payload["request"].get("model"),
                "internal_reasoning": "opaque",
                "stop_reason": response.get("stop_reason"),
                **({"token_count": token_count} if token_count is not None else {}),
                **({"usage": usage} if usage else {}),
            },
        )
    ]
    for index, block in enumerate(response.get("content") or []):
        if not isinstance(block, dict) or block.get("type") != "thinking":
            continue
        out.append(
            _fragment(
                f"anthropic_{round_payload['round_id']}_thinking_{index + 1}",
                FragmentKind.MODEL_GENERATION,
                timestamp=timestamp + 0.000051 + (index * 0.000001),
                stack_tier=opts.stack_tier,
                actor_id=actor_id,
                parent_trace_id=parent_trace_id,
                decision_id_hint=parent_trace_id,
                payload={
                    "model_id": response.get("model") or round_payload["request"].get("model"),
                    "internal_reasoning": "opaque",
                    "thinking": _thinking_payload(block, opts.store_thinking),
                },
            )
        )
    return out


def _response_message_fragments(
    round_payload: dict[str, Any],
    actor_id: str,
    opts: AnthropicIngestOptions,
) -> list[Fragment]:
    response = round_payload["response"]
    timestamp = float(round_payload["timestamp"])
    parent_trace_id = str(response.get("id") or round_payload["round_id"])
    out: list[Fragment] = []
    for index, block in enumerate(response.get("content") or []):
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        out.append(
            _fragment(
                f"anthropic_{round_payload['round_id']}_assistant_text_{index + 1}",
                FragmentKind.AGENT_MESSAGE,
                timestamp=timestamp + 0.0001 + (index * 0.000001),
                stack_tier=opts.stack_tier,
                actor_id=actor_id,
                parent_trace_id=parent_trace_id,
                decision_id_hint=parent_trace_id,
                payload={"content": block.get("text"), "role": "assistant"},
            )
        )
    return out
