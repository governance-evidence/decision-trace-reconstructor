"""Six-stage reconstruction pipeline.

Stages:
1. Fragment collection (input)
2. Temporal ordering
3. Chain assembly (trivial for single-scenario input -- all fragments belong
   to the target chain by construction)
4. Decision boundary detection
5. Decision-event schema mapping
6. Feasibility report
"""

from __future__ import annotations

from dataclasses import dataclass

from .core.architecture import Architecture, coerce_architecture
from .core.boundary import BoundaryConfig, detect_boundaries
from .core.chain import DecisionChain
from .core.fragment import Fragment, StackTier
from .core.temporal import order_fragments
from .mapping.feasibility import PropertyFeasibility
from .mapping.mapper import (
    map_chain_to_schema,
    map_chain_to_schema_aggregate,
    unrecoverable_mode_for_property,
)
from .mapping.operational_modes import OperationalMode, StructuralBreak, mode_to_break


@dataclass
class ReconstructionReport:
    """Output of the six-stage pipeline."""

    chain_id: str
    architecture: Architecture
    stack_tier: StackTier
    chain: DecisionChain
    per_unit_feasibility: dict[str, list[PropertyFeasibility]]
    completeness: float  # share of property-slots counting toward completeness
    total_property_slots: int
    unrecoverable_modes: list[OperationalMode]

    def dominant_mode(self) -> OperationalMode | None:
        if not self.unrecoverable_modes:
            return None
        counts: dict[OperationalMode, int] = {}
        for m in self.unrecoverable_modes:
            counts[m] = counts.get(m, 0) + 1
        return max(counts, key=lambda k: counts[k])

    def dominant_break(self) -> StructuralBreak | None:
        m = self.dominant_mode()
        return mode_to_break(m) if m else None


def reconstruct(
    fragments: list[Fragment],
    architecture: Architecture | str,
    stack_tier: StackTier,
    chain_id: str = "chain_0001",
    boundary_config: BoundaryConfig | None = None,
) -> ReconstructionReport:
    """Run the six-stage pipeline on a fragment list."""
    arch = coerce_architecture(architecture)
    ordered = order_fragments(fragments)
    units = detect_boundaries(ordered, boundary_config)
    chain = DecisionChain(chain_id=chain_id, units=units, source_fragments=ordered)
    per_unit = map_chain_to_schema(chain, arch, stack_tier)
    aggregated = map_chain_to_schema_aggregate(chain, arch, stack_tier)

    total = len(aggregated)
    completeness_score = (
        sum(f.contributes_to_completeness for f in aggregated) / total if total else 0.0
    )
    unrec_modes: list[OperationalMode] = []
    for f in aggregated:
        mode = unrecoverable_mode_for_property(f, arch, stack_tier)
        if mode is not None:
            unrec_modes.append(mode)

    return ReconstructionReport(
        chain_id=chain_id,
        architecture=arch,
        stack_tier=stack_tier,
        chain=chain,
        per_unit_feasibility=per_unit,
        completeness=completeness_score,
        total_property_slots=total,
        unrecoverable_modes=unrec_modes,
    )
