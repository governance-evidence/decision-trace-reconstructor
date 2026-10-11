"""Operational diagnoses require a recorded gap, not a topology label."""

from __future__ import annotations

from ..core.architecture import Architecture, coerce_architecture
from ..core.fragment import StackTier
from .feasibility import FeasibilityCategory, PropertyFeasibility
from .operational_modes import OperationalMode


def unrecoverable_mode_for_property(
    feas: PropertyFeasibility, architecture: Architecture | str, stack_tier: StackTier
) -> OperationalMode | None:
    """Missing fields alone do not establish a causal operational failure mode."""
    coerce_architecture(architecture)
    if (
        feas.category == FeasibilityCategory.STRUCTURALLY_UNFILLABLE
        and feas.gap_description == "matching payloads are explicitly opaque"
    ):
        return OperationalMode.MODE_3_CHANNEL_GAP
    return None


__all__ = ["unrecoverable_mode_for_property"]
