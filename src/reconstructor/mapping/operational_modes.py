"""Seven-mode operational failure rubric.

Each mode is mapped to one of the three theoretical structural breaks:
 - Decision diffusion: modes {1, 2, 5, 6}
 - Evidence fragmentation: modes {3, 4}
 - Responsibility ambiguity: mode {7}
"""

from __future__ import annotations

from enum import Enum


class OperationalMode(int, Enum):
    """Seven operational failure modes that account for unrecoverable decision-event properties."""

    MODE_1_NONLOCAL_DECISION = 1  # No single step can be identified as "the decision"
    MODE_2_CUMULATIVE_EFFECT = 2  # Outcome is the sum of many small agent steps
    MODE_3_CHANNEL_GAP = 3  # Evidence split across channels not all audited
    MODE_4_SCHEMA_MISMATCH = 4  # Evidence exists but in incompatible schemas
    MODE_5_DELEGATION_CHAIN = 5  # Decision delegated across multiple agents
    MODE_6_IMPLICIT_POLICY = 6  # Policy invoked implicitly, not recorded
    MODE_7_AUTHORSHIP_AMBIGUITY = 7  # Human and machine both claim partial authorship


class StructuralBreak(str, Enum):
    DECISION_DIFFUSION = "decision_diffusion"
    EVIDENCE_FRAGMENTATION = "evidence_fragmentation"
    RESPONSIBILITY_AMBIGUITY = "responsibility_ambiguity"


_MODE_TO_BREAK: dict[OperationalMode, StructuralBreak] = {
    OperationalMode.MODE_1_NONLOCAL_DECISION: StructuralBreak.DECISION_DIFFUSION,
    OperationalMode.MODE_2_CUMULATIVE_EFFECT: StructuralBreak.DECISION_DIFFUSION,
    OperationalMode.MODE_5_DELEGATION_CHAIN: StructuralBreak.DECISION_DIFFUSION,
    OperationalMode.MODE_6_IMPLICIT_POLICY: StructuralBreak.DECISION_DIFFUSION,
    OperationalMode.MODE_3_CHANNEL_GAP: StructuralBreak.EVIDENCE_FRAGMENTATION,
    OperationalMode.MODE_4_SCHEMA_MISMATCH: StructuralBreak.EVIDENCE_FRAGMENTATION,
    OperationalMode.MODE_7_AUTHORSHIP_AMBIGUITY: StructuralBreak.RESPONSIBILITY_AMBIGUITY,
}


def mode_to_break(mode: OperationalMode) -> StructuralBreak:
    """Map an operational mode to its theoretical structural break."""
    return _MODE_TO_BREAK[mode]
