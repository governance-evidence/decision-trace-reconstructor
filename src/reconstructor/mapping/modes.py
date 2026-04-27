"""Operational-mode mapping for unrecoverable decision-event properties."""

from __future__ import annotations

from ..core.architecture import Architecture, coerce_architecture
from ..core.fragment import StackTier
from .feasibility import FeasibilityCategory, PropertyFeasibility
from .operational_modes import OperationalMode
from .properties import DecisionEventProperty


def unrecoverable_mode_for_property(
    feas: PropertyFeasibility,
    architecture: Architecture | str,
    stack_tier: StackTier,
) -> OperationalMode | None:
    """For structurally-unfillable properties, name the dominant operational mode."""
    arch = coerce_architecture(architecture)
    if feas.category != FeasibilityCategory.STRUCTURALLY_UNFILLABLE:
        return None

    if stack_tier == StackTier.CROSS_STACK:
        return OperationalMode.MODE_3_CHANNEL_GAP

    if arch is Architecture.MULTI_AGENT:
        if feas.property_name in (DecisionEventProperty.POLICY_BASIS.value,):
            return OperationalMode.MODE_6_IMPLICIT_POLICY
        if feas.property_name in (
            DecisionEventProperty.INPUTS.value,
            DecisionEventProperty.OUTPUT_ACTION.value,
        ):
            return OperationalMode.MODE_5_DELEGATION_CHAIN
        return OperationalMode.MODE_1_NONLOCAL_DECISION

    if arch is Architecture.HUMAN_IN_THE_LOOP:
        return OperationalMode.MODE_7_AUTHORSHIP_AMBIGUITY

    if feas.property_name == DecisionEventProperty.REASONING_TRACE.value:
        return OperationalMode.MODE_2_CUMULATIVE_EFFECT

    return OperationalMode.MODE_4_SCHEMA_MISMATCH


__all__ = ["unrecoverable_mode_for_property"]
