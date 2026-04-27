"""Architecture and boundary-aware property classification rules."""

from __future__ import annotations

from ..core.architecture import Architecture
from ..core.chain import DecisionUnit
from ..core.fragment import Fragment, FragmentKind, StackTier
from .feasibility import FeasibilityCategory, PropertyFeasibility
from .feasibility_helpers import _unfillable_property
from .properties import DecisionEventProperty

_OPAQUE_PROPERTIES = {DecisionEventProperty.REASONING_TRACE}


def _classify_property(
    prop: DecisionEventProperty,
    unit: DecisionUnit,
    matching: list[Fragment],
    architecture: Architecture,
    stack_tier: StackTier,
) -> PropertyFeasibility:
    """Assign a feasibility category based on unit content and scenario profile."""
    result = _opaque_property_result(prop, unit)
    if result is not None:
        return result

    result = _cross_stack_property_result(prop, matching, stack_tier)
    if result is not None:
        return result

    result = _multi_agent_unit_result(prop, matching, unit, architecture)
    if result is not None:
        return result

    return _filled_or_unfilled_property(prop, matching)


def _opaque_property_result(
    prop: DecisionEventProperty,
    unit: DecisionUnit,
) -> PropertyFeasibility | None:
    if prop not in _OPAQUE_PROPERTIES:
        return None
    if not any(f.kind == FragmentKind.MODEL_GENERATION for f in unit.fragments):
        return None
    return PropertyFeasibility(
        property_name=prop.value,
        category=FeasibilityCategory.OPAQUE,
        value="<authorization_envelope>",
        gap_description=None,
        confidence=0.9,
    )


def _cross_stack_property_result(
    prop: DecisionEventProperty,
    matching: list[Fragment],
    stack_tier: StackTier,
) -> PropertyFeasibility | None:
    if stack_tier != StackTier.CROSS_STACK or prop not in (
        DecisionEventProperty.INPUTS,
        DecisionEventProperty.POST_CONDITION_STATE,
    ):
        return None

    if not matching:
        return _unfillable_property(
            prop,
            gap_description=f"cross-stack boundary discards {prop.value}",
        )
    return PropertyFeasibility(
        property_name=prop.value,
        category=FeasibilityCategory.PARTIALLY_FILLABLE,
        value=matching[0].payload,
        gap_description="cross-stack evidence partial",
        confidence=0.5,
    )


def _multi_agent_unit_result(
    prop: DecisionEventProperty,
    matching: list[Fragment],
    unit: DecisionUnit,
    architecture: Architecture,
) -> PropertyFeasibility | None:
    if architecture is not Architecture.MULTI_AGENT:
        return None

    actors = {f.actor_id for f in unit.fragments}
    actor_count = len(actors)
    if prop == DecisionEventProperty.OPERATOR_IDENTITY and actor_count > 2:
        return PropertyFeasibility(
            property_name=prop.value,
            category=FeasibilityCategory.PARTIALLY_FILLABLE,
            value=sorted(actors),
            gap_description=f"{actor_count} actors -- single operator identity ambiguous",
            confidence=0.5,
        )
    if prop == DecisionEventProperty.OUTPUT_ACTION and actor_count >= 2 and matching:
        return PropertyFeasibility(
            property_name=prop.value,
            category=FeasibilityCategory.PARTIALLY_FILLABLE,
            value=matching[0].payload,
            gap_description=f"output action delegated across {actor_count} agents",
            confidence=0.6,
        )
    if prop == DecisionEventProperty.POLICY_BASIS and not matching:
        return _unfillable_property(
            prop,
            gap_description="policy invoked implicitly across agents (mode 6)",
        )
    return None


def _filled_or_unfilled_property(
    prop: DecisionEventProperty,
    matching: list[Fragment],
) -> PropertyFeasibility:
    if not matching:
        return _unfillable_property(
            prop,
            gap_description=f"no {prop.value} fragment in unit",
        )

    if len(matching) == 1:
        return PropertyFeasibility(
            property_name=prop.value,
            category=FeasibilityCategory.FULLY_FILLABLE,
            value=matching[0].payload,
            gap_description=None,
            confidence=1.0,
        )

    return PropertyFeasibility(
        property_name=prop.value,
        category=FeasibilityCategory.FULLY_FILLABLE,
        value=[f.payload for f in matching],
        gap_description=None,
        confidence=1.0,
    )
