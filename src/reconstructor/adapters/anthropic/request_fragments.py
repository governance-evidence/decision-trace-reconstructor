"""Anthropic request fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import AnthropicIngestOptions
from .fragment_common import _fragment
from .message_payloads import _extract_cache_control, _user_message_text


def _request_snapshot_fragment(
    round_payload: dict[str, Any],
    actor_id: str,
    opts: AnthropicIngestOptions,
) -> Fragment:
    request = round_payload["request"]
    metadata = dict(request.get("metadata") or {})
    kind = FragmentKind.CONFIG_SNAPSHOT
    if metadata.get("demm_kind") == "policy_snapshot":
        kind = FragmentKind.POLICY_SNAPSHOT
    payload = {
        "model": request.get("model"),
        "system": request.get("system"),
        "tools": request.get("tools") or [],
        "metadata": metadata,
        "cache_control": _extract_cache_control(request),
    }
    if kind is FragmentKind.POLICY_SNAPSHOT:
        payload["constraint_activated"] = True
        payload["policy_id"] = metadata.get("policy_id") or "anthropic_request_policy"
    return _fragment(
        f"anthropic_{round_payload['round_id']}_request_snapshot",
        kind,
        timestamp=float(round_payload["timestamp"]),
        stack_tier=opts.stack_tier,
        actor_id=actor_id,
        parent_trace_id=str(round_payload["response"].get("id") or round_payload["round_id"]),
        decision_id_hint=str(round_payload["response"].get("id") or round_payload["round_id"]),
        payload=payload,
    )


def _request_message_fragments(
    round_payload: dict[str, Any],
    actor_id: str,
    opts: AnthropicIngestOptions,
) -> list[Fragment]:
    messages = round_payload["request"].get("messages") or []
    timestamp = float(round_payload["timestamp"])
    parent_trace_id = str(round_payload["response"].get("id") or round_payload["round_id"])
    out: list[Fragment] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        text_payload = _user_message_text(message.get("content"))
        if text_payload is None:
            continue
        out.append(
            _fragment(
                f"anthropic_{round_payload['round_id']}_user_{index + 1}",
                FragmentKind.AGENT_MESSAGE,
                timestamp=timestamp + (index * 0.00001),
                stack_tier=opts.stack_tier,
                actor_id=actor_id,
                parent_trace_id=parent_trace_id,
                decision_id_hint=parent_trace_id,
                payload={"content": text_payload, "role": "user"},
            )
        )
    return out
