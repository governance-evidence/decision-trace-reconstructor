"""Decision-event property to fragment-kind filler mapping."""

from __future__ import annotations

from ..core.chain import DecisionUnit
from ..core.fragment import Fragment, FragmentKind
from .properties import DecisionEventProperty

_PROPERTY_FILLERS: dict[DecisionEventProperty, tuple[FragmentKind, ...]] = {
    DecisionEventProperty.INPUTS: (FragmentKind.RETRIEVAL_RESULT, FragmentKind.AGENT_MESSAGE),
    DecisionEventProperty.POLICY_BASIS: (FragmentKind.POLICY_SNAPSHOT,),
    DecisionEventProperty.OPERATOR_IDENTITY: (
        FragmentKind.HUMAN_APPROVAL,
        FragmentKind.HUMAN_REJECTION,
        FragmentKind.AGENT_MESSAGE,
    ),
    DecisionEventProperty.AUTHORIZATION_ENVELOPE: (FragmentKind.CONFIG_SNAPSHOT,),
    DecisionEventProperty.REASONING_TRACE: (FragmentKind.MODEL_GENERATION,),
    DecisionEventProperty.OUTPUT_ACTION: (FragmentKind.TOOL_CALL, FragmentKind.STATE_MUTATION),
    DecisionEventProperty.POST_CONDITION_STATE: (FragmentKind.STATE_MUTATION,),
}


def _matching_fragments(prop: DecisionEventProperty, unit: DecisionUnit) -> list[Fragment]:
    fillers = _PROPERTY_FILLERS.get(prop, ())
    return [f for f in unit.fragments if f.kind in fillers]
