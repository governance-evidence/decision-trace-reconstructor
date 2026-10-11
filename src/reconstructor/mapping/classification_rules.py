"""Fragment coverage without topology or participant-count sufficiency penalties."""

from __future__ import annotations

from ..core.architecture import Architecture
from ..core.chain import DecisionUnit
from ..core.fragment import EvidenceVisibility, Fragment, FragmentKind, StackTier
from .feasibility import FeasibilityCategory, PropertyFeasibility
from .feasibility_helpers import _unfillable_property
from .properties import DecisionEventProperty


def _classify_property(
    prop: DecisionEventProperty,
    unit: DecisionUnit,
    matching: list[Fragment],
    architecture: Architecture,
    stack_tier: StackTier,
) -> PropertyFeasibility:
    # Architecture and tier remain API/context inputs, never evidence of a gap.
    if prop == DecisionEventProperty.REASONING_TRACE and any(
        f.kind == FragmentKind.MODEL_GENERATION for f in unit.fragments
    ):
        return PropertyFeasibility(
            prop.value, FeasibilityCategory.OPAQUE, "<authorization_envelope>", None, 0.9
        )
    if not matching:
        return _unfillable_property(prop, f"no {prop.value} fragment in unit")
    visible = [f for f in matching if f.evidence_visibility == EvidenceVisibility.VISIBLE]
    if visible:
        value = visible[0].payload if len(visible) == 1 else [f.payload for f in visible]
        return PropertyFeasibility(prop.value, FeasibilityCategory.FULLY_FILLABLE, value)
    if all(f.evidence_visibility == EvidenceVisibility.OPAQUE for f in matching):
        return _unfillable_property(prop, "matching payloads are explicitly opaque")
    return PropertyFeasibility(
        prop.value,
        FeasibilityCategory.PARTIALLY_FILLABLE,
        [f.payload for f in matching],
        "matching payload visibility is partial or unknown",
        0.5,
    )
