"""Bedrock ingest options."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core.fragment import StackTier


@dataclass(frozen=True)
class BedrockIngestOptions:
    architecture: str = "single_agent"
    stack_tier: StackTier = StackTier.WITHIN_STACK
    cross_stack_action_groups: tuple[str, ...] = field(default_factory=tuple)
    state_mutation_tool_pattern: str | None = None
    actor_override: str | None = None
    auto_architecture: bool = False
    store_content: bool = False
