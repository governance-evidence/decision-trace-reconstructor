"""Pydantic models for Generic JSONL mapping configuration schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .model_types import (
    GenericJsonlArchitecture,
    GenericJsonlFragmentKind,
    GenericJsonlStackTier,
)


class GenericJsonlMappingFields(BaseModel):
    """Field-path declarations for Generic JSONL record extraction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fragment_id: str | None = None
    timestamp: str = Field(min_length=1)
    actor_id: str | None = None
    payload: str | None = None


class GenericJsonlStateMutationPredicate(BaseModel):
    """Rule for emitting paired state-mutation fragments from tool records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str = Field(min_length=1)
    matches_regex: str = Field(min_length=1)


class GenericJsonlFollowupRule(BaseModel):
    """Rule for absorbing follow-up records into an earlier parent record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    absorbed_by_kind: str = Field(min_length=1)
    payload_key: str = Field(min_length=1)
    pair_match_field: str = Field(min_length=1)
    parent_match_field: str = Field(min_length=1)


class GenericJsonlMappingConfig(BaseModel):
    """Operator-supplied mapping config for the Generic JSONL fallback adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    source_name: str = Field(min_length=1)
    fields: GenericJsonlMappingFields
    kind_field: str = Field(min_length=1)
    kind_map: dict[str, GenericJsonlFragmentKind] = Field(min_length=1)
    skip_kinds: list[str] = Field(default_factory=list)
    state_mutation_predicate: GenericJsonlStateMutationPredicate | None = None
    absorb_followups: dict[str, GenericJsonlFollowupRule] = Field(default_factory=dict)
    stack_tier_field: str | None = None
    stack_tier_default: GenericJsonlStackTier = "within_stack"
    architecture: GenericJsonlArchitecture = "single_agent"

    @field_validator("kind_map")
    @classmethod
    def _validate_kind_map_non_empty(
        cls, value: dict[str, GenericJsonlFragmentKind]
    ) -> dict[str, GenericJsonlFragmentKind]:
        if not value:
            raise ValueError("kind_map must not be empty")
        return value

    @field_validator("skip_kinds")
    @classmethod
    def _validate_skip_kinds(cls, value: list[str]) -> list[str]:
        return [item for item in value if item]


__all__ = [
    "GenericJsonlFollowupRule",
    "GenericJsonlMappingConfig",
    "GenericJsonlMappingFields",
    "GenericJsonlStateMutationPredicate",
]
