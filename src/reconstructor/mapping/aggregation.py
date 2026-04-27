"""Chain-level decision-event property aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.architecture import Architecture, coerce_architecture
from ..core.chain import DecisionChain, DecisionUnit
from ..core.fragment import FragmentKind, StackTier
from .classification import _pick_best, _unfillable_property, map_chain_to_schema
from .feasibility import FeasibilityCategory, PropertyFeasibility
from .properties import ALL_DECISION_EVENT_PROPERTIES, DecisionEventProperty


@dataclass(frozen=True)
class _AggregateContext:
    all_actors: set[str]
    policy_unit_count: int
    unit_count: int


def map_chain_to_schema_aggregate(
    chain: DecisionChain,
    architecture: Architecture | str,
    stack_tier: StackTier,
) -> list[PropertyFeasibility]:
    """Produce one feasibility record per decision-event property for the whole chain.

    A decision event describes one decision; units are sub-steps. A
    property is considered fillable at chain level if any unit fills it.
    Dominant category precedence: FULLY_FILLABLE > OPAQUE >
    PARTIALLY_FILLABLE > STRUCTURALLY_UNFILLABLE.

    Architecture-aware downgrades then apply at chain level:
      - multi_agent: if >= 2 actors produced output fragments, OUTPUT_ACTION
        is downgraded because "the decision" cannot be localised to a single
        agent (decision diffusion, mode 1/5).
      - multi_agent: if units emit policy fragments inconsistently, POLICY_BASIS
        is downgraded (implicit policy, mode 6).
      - human_in_the_loop: OPERATOR_IDENTITY is at most PARTIAL because
        responsibility is shared between agent and human operator (mode 7).
    """
    arch = coerce_architecture(architecture)
    per_unit = map_chain_to_schema(chain, arch, stack_tier)
    context = _aggregate_context(chain)
    return [
        _aggregate_property(prop, per_unit, arch, context) for prop in ALL_DECISION_EVENT_PROPERTIES
    ]


def _aggregate_context(chain: DecisionChain) -> _AggregateContext:
    return _AggregateContext(
        all_actors={f.actor_id for f in chain.source_fragments},
        policy_unit_count=sum(1 for unit in chain.units if _unit_has_policy_snapshot(unit)),
        unit_count=len(chain.units),
    )


def _unit_has_policy_snapshot(unit: DecisionUnit) -> bool:
    return any(f.kind == FragmentKind.POLICY_SNAPSHOT for f in unit.fragments)


def _aggregate_property(
    prop: DecisionEventProperty,
    per_unit: dict[str, list[PropertyFeasibility]],
    architecture: Architecture,
    context: _AggregateContext,
) -> PropertyFeasibility:
    candidates = _property_candidates(prop, per_unit)
    if not candidates:
        return _unfillable_property(prop)
    best = _pick_best(candidates)
    return _apply_chain_architecture_adjustment(prop, best, architecture, context)


def _property_candidates(
    prop: DecisionEventProperty,
    per_unit: dict[str, list[PropertyFeasibility]],
) -> list[PropertyFeasibility]:
    return [
        feas
        for feas_list in per_unit.values()
        for feas in feas_list
        if feas.property_name == prop.value
    ]


def _apply_chain_architecture_adjustment(
    prop: DecisionEventProperty,
    best: PropertyFeasibility,
    architecture: Architecture,
    context: _AggregateContext,
) -> PropertyFeasibility:
    if architecture is Architecture.MULTI_AGENT:
        return _multi_agent_chain_adjustment(prop, best, context)
    if architecture is Architecture.HUMAN_IN_THE_LOOP:
        return _human_in_the_loop_chain_adjustment(prop, best)
    return best


def _multi_agent_chain_adjustment(
    prop: DecisionEventProperty,
    best: PropertyFeasibility,
    context: _AggregateContext,
) -> PropertyFeasibility:
    actor_count = len(context.all_actors)
    if prop == DecisionEventProperty.OUTPUT_ACTION and actor_count >= 3:
        return _unfillable_property(
            prop,
            gap_description=(
                f"decision diffused across {actor_count} agents -- "
                "no single authoritative output (mode 1/5)"
            ),
        )
    if prop == DecisionEventProperty.POLICY_BASIS and _policy_is_too_sparse(context):
        return _unfillable_property(
            prop,
            gap_description="policy invoked implicitly across agents (mode 6)",
        )
    if prop == DecisionEventProperty.OPERATOR_IDENTITY and actor_count >= 3:
        return PropertyFeasibility(
            property_name=prop.value,
            category=FeasibilityCategory.PARTIALLY_FILLABLE,
            value=sorted(context.all_actors),
            gap_description=(
                f"{actor_count} distinct actors across chain -- "
                "no single operator identity (delegation, mode 5)"
            ),
            confidence=0.5,
        )
    return best


def _policy_is_too_sparse(context: _AggregateContext) -> bool:
    return context.policy_unit_count < max(1, context.unit_count // 3)


def _human_in_the_loop_chain_adjustment(
    prop: DecisionEventProperty,
    best: PropertyFeasibility,
) -> PropertyFeasibility:
    if prop != DecisionEventProperty.OPERATOR_IDENTITY:
        return best
    if best.category not in (
        FeasibilityCategory.FULLY_FILLABLE,
        FeasibilityCategory.PARTIALLY_FILLABLE,
    ):
        return best
    return PropertyFeasibility(
        property_name=prop.value,
        category=FeasibilityCategory.PARTIALLY_FILLABLE,
        value=best.value,
        gap_description="shared authorship agent + operator (mode 7)",
        confidence=0.6,
    )


__all__ = ["map_chain_to_schema_aggregate"]
