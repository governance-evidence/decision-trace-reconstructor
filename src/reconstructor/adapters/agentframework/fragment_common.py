"""Shared helpers for Agent Framework fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import (
    _MANAGER_SENDERS,
    AgentFrameworkIngestOptions,
    _matches,
)


def _override_kind(payload: dict[str, Any]) -> FragmentKind | None:
    demm_kind = payload.get("demm_kind")
    if demm_kind == "policy_snapshot":
        return FragmentKind.POLICY_SNAPSHOT
    if demm_kind == "config_snapshot":
        return FragmentKind.CONFIG_SNAPSHOT
    return None


def _attach_round_context(fragment: Fragment, round_payload: dict[str, Any] | None) -> None:
    if round_payload:
        fragment.payload["round_context"] = round_payload


def _agent_scope(payload: dict[str, Any], event: dict[str, Any]) -> str:
    for field in ("agent_id", "agent_name"):
        if payload.get(field):
            return str(payload[field])
    if event.get("recipient"):
        return str(event["recipient"])
    if event.get("sender"):
        return str(event["sender"])
    return str(event["message_id"])


def _actor_id(event: dict[str, Any], opts: AgentFrameworkIngestOptions) -> str:
    if opts.actor_override:
        return opts.actor_override
    sender = str(event.get("sender") or "")
    if sender and sender.lower() in _MANAGER_SENDERS:
        return "manager"
    if sender:
        return sender
    payload = event["payload"]
    for field in ("agent_id", "agent_name"):
        if payload.get(field):
            return str(payload[field])
    return f"agent_{event['trace_id'][:8]}"


def _base_stack_tier(event: dict[str, Any], opts: AgentFrameworkIngestOptions) -> StackTier:
    return StackTier.CROSS_STACK if _runtime_mode(event, opts) == "grpc" else opts.stack_tier


def _tool_stack_tier(event: dict[str, Any], opts: AgentFrameworkIngestOptions) -> StackTier:
    payload = event["payload"]
    metadata = payload.get("metadata") or {}
    if _matches(payload.get("tool_name"), opts.cross_stack_tools_pattern):
        return StackTier.CROSS_STACK
    if str(metadata.get("host") or "").lower() == "azure_function":
        return StackTier.CROSS_STACK
    return _base_stack_tier(event, opts)


def _runtime_mode(event: dict[str, Any], opts: AgentFrameworkIngestOptions) -> str:
    if opts.runtime:
        return opts.runtime
    payload = event["payload"]
    metadata = payload.get("metadata") or {}
    runtime = (
        payload.get("runtime")
        or metadata.get("runtime")
        or metadata.get("transport")
        or "single_threaded"
    )
    runtime_text = str(runtime).lower()
    return "grpc" if "grpc" in runtime_text else "single_threaded"


def _fragment(
    event: dict[str, Any],
    kind: FragmentKind,
    *,
    suffix: str,
    actor_id: str,
    stack_tier: StackTier,
    payload: dict[str, Any],
    ts_offset: float = 0.0,
) -> Fragment:
    return Fragment(
        fragment_id=f"agentframework_{event['trace_id']}_{event['message_id']}_{suffix}",
        timestamp=float(event["timestamp"]) + ts_offset,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        payload=payload,
        parent_trace_id=event["trace_id"],
        decision_id_hint=event["message_id"],
    )
