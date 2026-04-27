"""Feasibility categories for decision-event property reconstruction.

In the method specification, each decision-event property is classified into one of four
categories. The category is itself a decision-event field so that downstream
controls can condition on reconstruction fidelity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FeasibilityCategory(str, Enum):
    """Four-way classification of property reconstruction feasibility."""

    FULLY_FILLABLE = "fully_fillable"
    PARTIALLY_FILLABLE = "partially_fillable"
    STRUCTURALLY_UNFILLABLE = "structurally_unfillable"
    OPAQUE = "opaque"  # ML-opacity boundary -- authorization envelope substituted


@dataclass
class PropertyFeasibility:
    """Per-property feasibility record."""

    property_name: str
    category: FeasibilityCategory
    value: object | None  # reconstructed value or None if unrecoverable
    gap_description: str | None = None  # populated for partial/unfillable
    confidence: float = 1.0  # 0.0 -- 1.0

    @property
    def contributes_to_completeness(self) -> float:
        """Share of this property counting toward completeness metric.

        Fully fillable and opaque (envelope-substituted) count as 1.0.
        Partially fillable contributes fractionally via confidence.
        Structurally unfillable contributes 0.0.
        """
        if self.category in (
            FeasibilityCategory.FULLY_FILLABLE,
            FeasibilityCategory.OPAQUE,
        ):
            return 1.0
        if self.category == FeasibilityCategory.PARTIALLY_FILLABLE:
            return self.confidence
        return 0.0
