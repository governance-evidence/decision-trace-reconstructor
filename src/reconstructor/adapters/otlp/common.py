"""Shared OTLP adapter options and low-level helpers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from ...core.fragment import FragmentKind, StackTier


@dataclass(frozen=True)
class OtlpIngestOptions:
    """Operator-supplied OTLP ingest parameters."""

    architecture: str = "single_agent"
    stack_tier: StackTier = StackTier.WITHIN_STACK
    within_stack_services: tuple[str, ...] = field(default_factory=tuple)
    state_mutation_tool_pattern: str | None = None
    actor_override: str | None = None
    accept_sampled: bool = False
    sampling_rate: float | None = None
    store_content: bool = False
    auto_architecture: bool = False
    schema_version_tolerance: str = "lenient"


def _merged_attrs(span: dict[str, Any]) -> dict[str, Any]:
    return {**span.get("resource", {}), **span.get("attributes", {})}


def _get_attr(span: dict[str, Any], *keys: str) -> Any:
    attrs = _merged_attrs(span)
    for key in keys:
        if key in attrs and attrs[key] not in (None, ""):
            return attrs[key]
    return None


def _actor_id(span: dict[str, Any], opts: OtlpIngestOptions) -> str:
    if opts.actor_override:
        return opts.actor_override
    for value in (
        _get_attr(span, "gen_ai.agent.id"),
        _get_attr(span, "gen_ai.agent.name"),
        _get_attr(span, "service.name"),
        span.get("name"),
    ):
        if value:
            return str(value)
    return f"agent_{span['span_id'][:8]}"


def _stack_tier_for(span: dict[str, Any], opts: OtlpIngestOptions) -> StackTier:
    override = _get_attr(span, "demm.stack_tier")
    if override:
        try:
            return StackTier(str(override))
        except ValueError:
            pass
    if _get_attr(span, "mcp.session.id"):
        return StackTier.CROSS_STACK
    server_address = _get_attr(span, "server.address")
    if span.get("kind") == "client" and server_address and opts.within_stack_services:
        if str(server_address) not in set(opts.within_stack_services):
            return StackTier.CROSS_STACK
    return opts.stack_tier


def _span_override_kind(span: dict[str, Any]) -> FragmentKind | None:
    raw = _get_attr(span, "demm.fragment_kind")
    if not raw:
        return None
    try:
        return FragmentKind(str(raw))
    except ValueError:
        return None


def _operation_name(span: dict[str, Any]) -> str:
    return str(_get_attr(span, "gen_ai.operation.name") or "").lower()


def _content_field(payload: Any, store_content: bool) -> Any:
    if payload is None:
        return None
    if store_content:
        return payload
    if isinstance(payload, str):
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return {"sha256": digest, "length": len(payload)}
    encoded = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {"sha256": digest, "length": len(encoded)}


def _is_state_mutating(tool_name: str | None, opts: OtlpIngestOptions) -> bool:
    if not tool_name or not opts.state_mutation_tool_pattern:
        return False
    return re.search(opts.state_mutation_tool_pattern, tool_name, re.IGNORECASE) is not None


__all__ = ["OtlpIngestOptions"]
