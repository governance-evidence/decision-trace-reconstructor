"""Decision boundary detection.

Stage 4 of the reconstruction pipeline. Partitions an ordered fragment
sequence into DecisionUnits using four configurable heuristics:

1. State-change magnitude -- large state deviation marks a boundary
2. Tool-call boundaries -- every tool call is a boundary candidate
3. Human intervention -- explicit approvals/rejections are unambiguous boundaries
4. Policy-constraint activation -- constraint firing marks a boundary

Each placed boundary carries a confidence score.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chain import DecisionUnit
from .fragment import Fragment, FragmentKind


@dataclass
class BoundaryConfig:
    """Configuration for boundary heuristics."""

    state_change_threshold: float = 0.5  # payload magnitude delta triggering a boundary
    tool_call_confidence: float = 0.8
    human_intervention_confidence: float = 1.0  # always confident
    policy_activation_confidence: float = 0.9
    state_change_confidence: float = 0.6


def detect_boundaries(
    fragments: list[Fragment],
    config: BoundaryConfig | None = None,
) -> list[DecisionUnit]:
    """Partition an ordered fragment sequence into decision units.

    Returns a list of DecisionUnits; each unit contains consecutive
    fragments between two boundary markers.
    """
    cfg = config or BoundaryConfig()
    if not fragments:
        return []

    units: list[DecisionUnit] = []
    current_frags: list[Fragment] = []
    current_reason = "initial"
    current_conf = 0.5

    for frag in fragments:
        is_boundary, reason, conf = _is_boundary(frag, cfg)
        if is_boundary and current_frags:
            units.append(
                DecisionUnit(
                    unit_id=f"unit_{len(units):04d}",
                    fragments=current_frags,
                    boundary_reason=current_reason,
                    boundary_confidence=current_conf,
                )
            )
            current_frags = [frag]
            current_reason = reason
            current_conf = conf
        else:
            current_frags.append(frag)
            if is_boundary:
                current_reason = reason
                current_conf = conf

    if current_frags:
        units.append(
            DecisionUnit(
                unit_id=f"unit_{len(units):04d}",
                fragments=current_frags,
                boundary_reason=current_reason,
                boundary_confidence=current_conf,
            )
        )
    return units


def _is_boundary(frag: Fragment, cfg: BoundaryConfig) -> tuple[bool, str, float]:
    """Evaluate a fragment against the four heuristics.

    Returns (is_boundary, reason, confidence).
    """
    if frag.is_human_intervention():
        return True, "human", cfg.human_intervention_confidence
    if frag.is_policy_trigger():
        return True, "policy", cfg.policy_activation_confidence
    if frag.is_tool_call():
        return True, "tool_call", cfg.tool_call_confidence
    if frag.kind == FragmentKind.STATE_MUTATION:
        magnitude = float(frag.payload.get("state_change_magnitude", 0.0))
        if magnitude >= cfg.state_change_threshold:
            return True, "state_change", cfg.state_change_confidence
    return False, "no_boundary", 0.0
