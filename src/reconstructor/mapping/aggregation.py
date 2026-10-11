"""Chain aggregation: fragment coverage or explicit decision-evidence obligations."""

from __future__ import annotations

from ..core.architecture import Architecture
from ..core.chain import DecisionChain
from ..core.fragment import StackTier
from .classification import _pick_best, _unfillable_property, map_chain_to_schema
from .evidence_contract import (
    CONTRACTS,
    COVERAGE_CONTRACT,
    DECISION_CONTRACT,
    assess_decision_evidence,
)
from .feasibility import PropertyFeasibility
from .properties import ALL_DECISION_EVENT_PROPERTIES


def map_chain_to_schema_aggregate(
    chain: DecisionChain,
    architecture: Architecture | str,
    stack_tier: StackTier,
    evidence_contract: str = COVERAGE_CONTRACT,
) -> list[PropertyFeasibility]:
    """Aggregate coverage; typed checks use all records, not best-unit evidence.

    Neither several participants, several action issuers, a human reviewer nor a
    service boundary establishes an evidence deficit by itself. The opt-in typed
    contract checks bindings and content; legacy manifests report coverage only.
    """
    if evidence_contract not in CONTRACTS:
        raise ValueError(f"unknown evidence contract: {evidence_contract}")
    per_unit = map_chain_to_schema(chain, architecture, stack_tier)
    coverage = []
    for prop in ALL_DECISION_EVENT_PROPERTIES:
        candidates = [
            f for items in per_unit.values() for f in items if f.property_name == prop.value
        ]
        coverage.append(_pick_best(candidates) if candidates else _unfillable_property(prop))
    if evidence_contract == DECISION_CONTRACT:
        return assess_decision_evidence(chain, coverage)
    return coverage


__all__ = ["map_chain_to_schema_aggregate"]
