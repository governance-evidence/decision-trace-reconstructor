"""Shared helpers for decision-event property feasibility results."""

from __future__ import annotations

from .feasibility import FeasibilityCategory, PropertyFeasibility
from .properties import DecisionEventProperty


def _unfillable_property(
    prop: DecisionEventProperty,
    gap_description: str | None = None,
) -> PropertyFeasibility:
    return PropertyFeasibility(
        property_name=prop.value,
        category=FeasibilityCategory.STRUCTURALLY_UNFILLABLE,
        value=None,
        gap_description=gap_description,
        confidence=0.0,
    )


def _pick_best(cands: list[PropertyFeasibility]) -> PropertyFeasibility:
    """Pick the strongest feasibility among candidates for the same property."""
    precedence = {
        FeasibilityCategory.FULLY_FILLABLE: 4,
        FeasibilityCategory.OPAQUE: 3,
        FeasibilityCategory.PARTIALLY_FILLABLE: 2,
        FeasibilityCategory.STRUCTURALLY_UNFILLABLE: 1,
    }
    return max(cands, key=lambda f: (precedence[f.category], f.confidence))
