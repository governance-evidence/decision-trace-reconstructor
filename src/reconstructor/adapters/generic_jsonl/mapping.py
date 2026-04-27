"""Generic JSONL mapping configuration normalisation."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ...core.fragment import FragmentKind, StackTier
from ...output.models import GenericJsonlMappingConfig
from .common import (
    FollowupRule,
    GenericJsonlMapping,
    MappingFields,
    StateMutationPredicate,
)


def _normalise_mapping(data: Any) -> GenericJsonlMapping:
    try:
        config = GenericJsonlMappingConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(_format_mapping_validation_error(exc)) from exc

    return GenericJsonlMapping(
        schema_version=config.schema_version,
        source_name=config.source_name,
        fields=_mapping_fields(config),
        kind_field=config.kind_field,
        kind_map=_kind_map(config),
        skip_kinds=tuple(str(item) for item in config.skip_kinds),
        state_mutation_predicate=_state_mutation_predicate(config),
        absorb_followups=_followup_rules(config),
        stack_tier_field=config.stack_tier_field,
        stack_tier_default=StackTier(config.stack_tier_default),
        architecture=config.architecture,
    )


def _mapping_fields(config: GenericJsonlMappingConfig) -> MappingFields:
    return MappingFields(
        timestamp=config.fields.timestamp,
        fragment_id=config.fields.fragment_id,
        actor_id=config.fields.actor_id,
        payload=config.fields.payload,
    )


def _kind_map(config: GenericJsonlMappingConfig) -> dict[str, FragmentKind]:
    out: dict[str, FragmentKind] = {}
    for raw_kind, mapped_value in config.kind_map.items():
        try:
            out[str(raw_kind)] = FragmentKind(str(mapped_value))
        except ValueError as exc:
            valid = ", ".join(sorted(item.value for item in FragmentKind))
            raise ValueError(
                f"kind_map contains invalid FragmentKind {mapped_value!r}. Valid values: {valid}"
            ) from exc
    return out


def _state_mutation_predicate(
    config: GenericJsonlMappingConfig,
) -> StateMutationPredicate | None:
    if config.state_mutation_predicate is None:
        return None
    return StateMutationPredicate(
        field=config.state_mutation_predicate.field,
        matches_regex=config.state_mutation_predicate.matches_regex,
    )


def _followup_rules(config: GenericJsonlMappingConfig) -> dict[str, FollowupRule]:
    out: dict[str, FollowupRule] = {}
    for followup_kind, rule in config.absorb_followups.items():
        out[str(followup_kind)] = FollowupRule(
            absorbed_by_kind=rule.absorbed_by_kind,
            payload_key=rule.payload_key,
            pair_match_field=rule.pair_match_field,
            parent_match_field=rule.parent_match_field,
        )
    return out


def _format_mapping_validation_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    if location == "schema_version":
        value = first.get("input")
        return f"unknown schema_version {value!r}; expected '1.0'"
    if location == "fields":
        return "mapping config requires a 'fields' object"
    if location == "fields.timestamp":
        return "mapping config requires fields.timestamp as a non-empty string"
    if location == "kind_field":
        return "mapping config requires kind_field as a non-empty string"
    if location == "kind_map":
        value = first.get("input")
        if value in ({}, None):
            return "mapping config requires a non-empty kind_map"
        return "mapping config requires a non-empty kind_map"
    if location.startswith("kind_map."):
        value = first.get("input")
        valid = ", ".join(sorted(item.value for item in FragmentKind))
        return f"kind_map contains invalid FragmentKind {value!r}. Valid values: {valid}"
    return (
        f"invalid mapping config at {location or '<root>'}: {first.get('msg', 'validation failed')}"
    )
