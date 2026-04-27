"""Decision-event schema property classes used for feasibility reports.

This is a prototype mapping. The authoritative schema lives in the
decision-event-schema repository (sibling project). Here we enumerate the
property classes that §5 per-property feasibility analysis refers to.
"""

from __future__ import annotations

from enum import Enum


class DecisionEventProperty(str, Enum):
    """Decision-event property classes used by the reconstructability report."""

    INPUTS = "inputs"
    POLICY_BASIS = "policy_basis"
    OPERATOR_IDENTITY = "operator_identity"
    AUTHORIZATION_ENVELOPE = "authorization_envelope"
    REASONING_TRACE = "reasoning_trace"
    OUTPUT_ACTION = "output_action"
    POST_CONDITION_STATE = "post_condition_state"


ALL_DECISION_EVENT_PROPERTIES: list[DecisionEventProperty] = list(DecisionEventProperty)
