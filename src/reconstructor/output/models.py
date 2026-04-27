"""Public Pydantic model facade for result artifacts and operator configs.

These models are the canonical schema for the four result files emitted by the
run scripts and for the Generic JSONL fallback mapping config. The concrete
classes live in smaller modules; this facade preserves the historical
``reconstructor.output.models`` import path.
"""

from __future__ import annotations

from .generic_jsonl_models import (
    GenericJsonlFollowupRule,
    GenericJsonlMappingConfig,
    GenericJsonlMappingFields,
    GenericJsonlStateMutationPredicate,
)
from .model_types import (
    Architecture,
    DecisionEventProperty,
    FeasibilityCategory,
    GenericJsonlArchitecture,
    GenericJsonlFragmentKind,
    GenericJsonlStackTier,
    OperationalMode,
    StackTier,
    StructuralBreak,
)
from .result_models import (
    CellResult,
    CellResults,
    FeasibilityCounts,
    NamedIncidentResult,
    NamedIncidentResults,
    PerPropertyFeasibility,
    PerPropertyTable,
    PerScenarioResult,
    PerScenarioResults,
    PropertyDistribution,
)

__all__ = [
    "Architecture",
    "CellResult",
    "CellResults",
    "DecisionEventProperty",
    "FeasibilityCategory",
    "FeasibilityCounts",
    "GenericJsonlArchitecture",
    "GenericJsonlFollowupRule",
    "GenericJsonlFragmentKind",
    "GenericJsonlMappingConfig",
    "GenericJsonlMappingFields",
    "GenericJsonlStackTier",
    "GenericJsonlStateMutationPredicate",
    "NamedIncidentResult",
    "NamedIncidentResults",
    "OperationalMode",
    "PerPropertyFeasibility",
    "PerPropertyTable",
    "PerScenarioResult",
    "PerScenarioResults",
    "PropertyDistribution",
    "StackTier",
    "StructuralBreak",
]
