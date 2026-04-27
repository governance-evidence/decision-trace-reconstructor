"""Literal types shared by output artifact schemas."""

from __future__ import annotations

from typing import Literal

# These intentionally mirror the runtime enums in ``mapping/feasibility.py``,
# ``mapping/operational_modes.py``, and ``core/fragment.py``. They remain
# Literal types so schema generation does not need to import runtime objects.

Architecture = Literal[
    "single_agent",
    "multi_agent",
    "human_in_the_loop",
    "non_agentic",
]

StackTier = Literal["within_stack", "cross_stack", "baseline"]

GenericJsonlStackTier = Literal["within_stack", "cross_stack", "human"]

GenericJsonlFragmentKind = Literal[
    "tool_call",
    "model_generation",
    "human_approval",
    "human_rejection",
    "policy_snapshot",
    "config_snapshot",
    "agent_message",
    "retrieval_result",
    "state_mutation",
    "error",
]

GenericJsonlArchitecture = Literal[
    "single_agent",
    "multi_agent",
    "human_in_the_loop",
    "auto",
]

FeasibilityCategory = Literal[
    "fully_fillable",
    "partially_fillable",
    "structurally_unfillable",
    "opaque",
]

DecisionEventProperty = Literal[
    "inputs",
    "policy_basis",
    "operator_identity",
    "authorization_envelope",
    "reasoning_trace",
    "output_action",
    "post_condition_state",
]

StructuralBreak = Literal[
    "decision_diffusion",
    "evidence_fragmentation",
    "responsibility_ambiguity",
]

OperationalMode = Literal[1, 2, 3, 4, 5, 6, 7]

__all__ = [
    "Architecture",
    "DecisionEventProperty",
    "FeasibilityCategory",
    "GenericJsonlArchitecture",
    "GenericJsonlFragmentKind",
    "GenericJsonlStackTier",
    "OperationalMode",
    "StackTier",
    "StructuralBreak",
]
