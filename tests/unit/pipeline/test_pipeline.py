"""Pipeline-level tests covering boundary detection, decision-event mapping, and feasibility.

These tests exercise the actual reconstruction logic (six-stage pipeline)
rather than the output serialization layer. They establish a coverage floor
for the parts of the system the §5 evaluation depends on.
"""

from __future__ import annotations

from reconstructor.core.boundary import BoundaryConfig, detect_boundaries
from reconstructor.core.chain import DecisionChain
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.mapping.feasibility import FeasibilityCategory, PropertyFeasibility
from reconstructor.mapping.mapper import (
    map_chain_to_schema_aggregate,
    unrecoverable_mode_for_property,
)
from reconstructor.mapping.operational_modes import OperationalMode, mode_to_break
from reconstructor.pipeline import reconstruct
from reconstructor.synthetic.named_incidents import (
    claude_code_datatalks_drop_database,
    cursor_destructive_command,
    replit_drop_database,
)

# ---------------------------------------------------------------------------
# Boundary detection
# ---------------------------------------------------------------------------


def _frag(fid: str, t: float, kind: FragmentKind, **payload: object) -> Fragment:
    return Fragment(
        fragment_id=fid,
        timestamp=t,
        kind=kind,
        stack_tier=StackTier.WITHIN_STACK,
        actor_id="agent_test",
        payload=dict(payload),
    )


def test_detect_boundaries_handles_empty_input() -> None:
    assert detect_boundaries([]) == []


def test_detect_boundaries_treats_human_approval_as_boundary() -> None:
    frags = [
        _frag("f0", 0.0, FragmentKind.MODEL_GENERATION),
        _frag("f1", 1.0, FragmentKind.HUMAN_APPROVAL),
        _frag("f2", 2.0, FragmentKind.MODEL_GENERATION),
    ]
    units = detect_boundaries(frags)
    # First unit is the model generation, second starts at the human approval.
    assert len(units) >= 2
    assert any(u.boundary_reason == "human" for u in units)


def test_detect_boundaries_state_change_threshold() -> None:
    cfg = BoundaryConfig(state_change_threshold=0.5)
    # Below threshold: not a boundary.
    below = _frag("f0", 0.0, FragmentKind.STATE_MUTATION, state_change_magnitude=0.4)
    above = _frag("f1", 1.0, FragmentKind.STATE_MUTATION, state_change_magnitude=0.6)
    units = detect_boundaries([below, above], cfg)
    assert any(u.boundary_reason == "state_change" for u in units)


def test_detect_boundaries_policy_trigger_only_when_constraint_active() -> None:
    inactive = _frag("p0", 0.0, FragmentKind.POLICY_SNAPSHOT, constraint_activated=False)
    active = _frag("p1", 1.0, FragmentKind.POLICY_SNAPSHOT, constraint_activated=True)
    units = detect_boundaries([inactive, active])
    assert any(u.boundary_reason == "policy" for u in units)
    # The inactive policy snapshot should NOT have triggered a boundary.
    assert not any(
        u.boundary_reason == "policy" and any(f.fragment_id == "p0" for f in u.fragments)
        for u in units
    )


# ---------------------------------------------------------------------------
# Decision-event mapping + feasibility
# ---------------------------------------------------------------------------


def test_replit_incident_yields_expected_dominant_break() -> None:
    sc = replit_drop_database()
    report = reconstruct(
        fragments=sc.fragments,
        architecture=sc.architecture,
        stack_tier=sc.stack_tier,
        chain_id=sc.scenario_id,
    )
    assert report.dominant_break() is not None
    assert report.dominant_break().value == "evidence_fragmentation"


def test_named_incidents_have_consistent_completeness() -> None:
    """All three single_agent x cross_stack incidents should reconstruct
    to the same per-property profile.

    We don't pin the exact completeness float (4/7 from 2 fully + 1 opaque +
    2 partial * 0.5); instead we pin the qualitative invariants below.
    """
    for sc in (
        replit_drop_database(),
        cursor_destructive_command(),
        claude_code_datatalks_drop_database(),
    ):
        r = reconstruct(
            fragments=sc.fragments,
            architecture=sc.architecture,
            stack_tier=sc.stack_tier,
            chain_id=sc.scenario_id,
        )
        # Single-agent cross-stack -> dominant break is evidence_fragmentation.
        assert r.dominant_break().value == "evidence_fragmentation"
        # Reasoning trace must be opaque (substituted by authorization envelope).
        agg = map_chain_to_schema_aggregate(r.chain, sc.architecture, sc.stack_tier)
        rt = next(f for f in agg if f.property_name == "reasoning_trace")
        assert rt.category == FeasibilityCategory.OPAQUE


def test_property_feasibility_completeness_score() -> None:
    """Fully and opaque count as 1.0; structurally_unfillable as 0.0."""
    fully = PropertyFeasibility(
        property_name="x",
        category=FeasibilityCategory.FULLY_FILLABLE,
        value=None,
    )
    opaque = PropertyFeasibility(
        property_name="x",
        category=FeasibilityCategory.OPAQUE,
        value=None,
    )
    partial = PropertyFeasibility(
        property_name="x",
        category=FeasibilityCategory.PARTIALLY_FILLABLE,
        value=None,
        confidence=0.7,
    )
    unfill = PropertyFeasibility(
        property_name="x",
        category=FeasibilityCategory.STRUCTURALLY_UNFILLABLE,
        value=None,
    )
    assert fully.contributes_to_completeness == 1.0
    assert opaque.contributes_to_completeness == 1.0
    assert partial.contributes_to_completeness == 0.7
    assert unfill.contributes_to_completeness == 0.0


# ---------------------------------------------------------------------------
# Operational modes
# ---------------------------------------------------------------------------


def test_mode_to_break_is_total_function() -> None:
    """Every operational mode maps to exactly one structural break."""
    for mode in OperationalMode:
        result = mode_to_break(mode)
        assert result.value in (
            "decision_diffusion",
            "evidence_fragmentation",
            "responsibility_ambiguity",
        )


def test_unrecoverable_mode_is_none_for_filled_property() -> None:
    feas = PropertyFeasibility(
        property_name="inputs",
        category=FeasibilityCategory.FULLY_FILLABLE,
        value=None,
    )
    assert unrecoverable_mode_for_property(feas, "single_agent", StackTier.WITHIN_STACK) is None


def test_unrecoverable_mode_cross_stack_is_channel_gap() -> None:
    feas = PropertyFeasibility(
        property_name="inputs",
        category=FeasibilityCategory.STRUCTURALLY_UNFILLABLE,
        value=None,
    )
    mode = unrecoverable_mode_for_property(feas, "single_agent", StackTier.CROSS_STACK)
    assert mode is OperationalMode.MODE_3_CHANNEL_GAP


def test_decision_chain_metrics() -> None:
    """DecisionChain length() and fragment_count() reflect contents."""
    units = [
        type(
            "U",
            (),
            {
                "unit_id": "u0",
                "fragments": [_frag("a", 0.0, FragmentKind.TOOL_CALL)],
                "boundary_reason": "tool_call",
                "boundary_confidence": 0.8,
                "start_timestamp": lambda self=None: 0.0,
                "end_timestamp": lambda self=None: 0.0,
                "primary_actor": lambda self=None: "agent_test",
            },
        )(),
    ]
    chain = DecisionChain(chain_id="c", units=units, source_fragments=units[0].fragments)
    assert chain.length() == 1
    assert chain.fragment_count() == 1
