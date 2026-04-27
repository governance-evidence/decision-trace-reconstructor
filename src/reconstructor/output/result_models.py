"""Pydantic models for canonical evaluation result artifacts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, RootModel

from .model_types import (
    Architecture,
    DecisionEventProperty,
    FeasibilityCategory,
    OperationalMode,
    StackTier,
    StructuralBreak,
)


class CellResult(BaseModel):
    """One row of ``cells.json``: aggregate statistics for one matrix cell."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    architecture: Architecture
    stack_tier: StackTier
    n: int = Field(ge=0, description="Number of scenarios aggregated into this cell.")
    completeness_pct: float = Field(ge=0.0, le=100.0)
    completeness_ci_low: float = Field(ge=0.0, le=100.0)
    completeness_ci_high: float = Field(ge=0.0, le=100.0)
    boundary_f1: float = Field(ge=0.0, le=1.0)
    modal_mode: OperationalMode | None = Field(
        default=None,
        description="7-mode operational-failure dominance: modal mode across "
        "unrecoverable properties, or null when no failures observed.",
    )
    modal_mode_share: float = Field(ge=0.0, le=1.0)
    dominant_break: StructuralBreak | None = None


class CellResults(RootModel[list[CellResult]]):
    """Root model for ``cells.json`` (a JSON array)."""


class PropertyDistribution(BaseModel):
    """Feasibility-category distribution for a single decision-event property."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fully_fillable: float = Field(ge=0.0, le=100.0, default=0.0)
    partially_fillable: float = Field(ge=0.0, le=100.0, default=0.0)
    structurally_unfillable: float = Field(ge=0.0, le=100.0, default=0.0)
    opaque: float = Field(ge=0.0, le=100.0, default=0.0)


class PerPropertyTable(RootModel[dict[DecisionEventProperty, PropertyDistribution]]):
    """Root model for ``per_property.json``."""


class PerScenarioResult(BaseModel):
    """One row of ``per_scenario.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: str = Field(min_length=1)
    architecture: Architecture
    stack_tier: StackTier
    seed: int
    fragments: int = Field(ge=0)
    units_detected: int = Field(ge=0)
    completeness: float = Field(ge=0.0, le=1.0)
    boundary_f1: float = Field(ge=0.0, le=1.0)
    unrecoverable_mode_count: int = Field(ge=0)
    dominant_mode: OperationalMode | None = None
    dominant_break: StructuralBreak | None = None


class PerScenarioResults(RootModel[list[PerScenarioResult]]):
    """Root model for ``per_scenario.json``."""


class FeasibilityCounts(BaseModel):
    """Histogram of feasibility categories across the 7 decision-event properties."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fully_fillable: int = Field(ge=0, default=0)
    partially_fillable: int = Field(ge=0, default=0)
    structurally_unfillable: int = Field(ge=0, default=0)
    opaque: int = Field(ge=0, default=0)


class PerPropertyFeasibility(BaseModel):
    """Per-property feasibility record inside a named-incident result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    property: DecisionEventProperty
    category: FeasibilityCategory
    gap: str | None = None


class NamedIncidentResult(BaseModel):
    """One row of ``named_incidents.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    incident: str = Field(min_length=1)
    architecture: Architecture
    stack_tier: StackTier
    fragments: int = Field(ge=0)
    units_detected: int = Field(ge=0)
    completeness_pct: float = Field(ge=0.0, le=100.0)
    dominant_mode: OperationalMode | None = None
    dominant_break: StructuralBreak | None = None
    feasibility_counts: FeasibilityCounts
    per_property: list[PerPropertyFeasibility] = Field(default_factory=list)


class NamedIncidentResults(RootModel[list[NamedIncidentResult]]):
    """Root model for ``named_incidents.json``."""


__all__ = [
    "CellResult",
    "CellResults",
    "FeasibilityCounts",
    "NamedIncidentResult",
    "NamedIncidentResults",
    "PerPropertyFeasibility",
    "PerPropertyTable",
    "PerScenarioResult",
    "PerScenarioResults",
    "PropertyDistribution",
]
