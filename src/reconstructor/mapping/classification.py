"""Per-unit decision-event property classification."""

from __future__ import annotations

from ..core.architecture import Architecture, coerce_architecture
from ..core.chain import DecisionChain, DecisionUnit
from ..core.fragment import StackTier
from .classification_rules import _classify_property
from .feasibility import PropertyFeasibility
from .feasibility_helpers import _pick_best, _unfillable_property
from .properties import ALL_DECISION_EVENT_PROPERTIES
from .property_fillers import _matching_fragments


def map_unit_to_schema(
    unit: DecisionUnit,
    architecture: Architecture | str,
    stack_tier: StackTier,
) -> list[PropertyFeasibility]:
    """Project a decision unit onto decision-event property feasibility records."""
    arch = coerce_architecture(architecture)
    return [
        _classify_property(prop, unit, _matching_fragments(prop, unit), arch, stack_tier)
        for prop in ALL_DECISION_EVENT_PROPERTIES
    ]


def map_chain_to_schema(
    chain: DecisionChain,
    architecture: Architecture | str,
    stack_tier: StackTier,
) -> dict[str, list[PropertyFeasibility]]:
    """Map an entire chain to per-unit decision-event feasibility records."""
    arch = coerce_architecture(architecture)
    return {unit.unit_id: map_unit_to_schema(unit, arch, stack_tier) for unit in chain.units}


__all__ = ["_pick_best", "_unfillable_property", "map_chain_to_schema", "map_unit_to_schema"]
