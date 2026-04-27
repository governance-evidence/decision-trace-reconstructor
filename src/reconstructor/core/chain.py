"""Decision chain data model.

A DecisionChain is an ordered sequence of DecisionUnits, each of which
corresponds to a bounded decision (identified by §3.3 boundary heuristics).
A chain is the output of Stage 3 (chain assembly) and the input to Stage 4
(boundary detection) of the reconstruction pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .fragment import Fragment


@dataclass
class DecisionUnit:
    """A bounded decision made up of one or more fragments.

    Boundaries are set by §3.3 heuristics. Each unit carries a confidence
    score that reflects boundary-placement certainty.
    """

    unit_id: str
    fragments: list[Fragment]
    boundary_reason: str  # "state_change", "tool_call", "human", "policy"
    boundary_confidence: float  # 0.0 -- 1.0

    def start_timestamp(self) -> float:
        return min(f.timestamp for f in self.fragments)

    def end_timestamp(self) -> float:
        return max(f.timestamp for f in self.fragments)

    def primary_actor(self) -> str:
        """Most common actor across fragments."""
        counts: dict[str, int] = {}
        for f in self.fragments:
            counts[f.actor_id] = counts.get(f.actor_id, 0) + 1
        return max(counts, key=lambda k: counts[k])


@dataclass
class DecisionChain:
    """An ordered sequence of decision units representing a single agent
    execution targeted for reconstruction.
    """

    chain_id: str
    units: list[DecisionUnit] = field(default_factory=list)
    source_fragments: list[Fragment] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def length(self) -> int:
        return len(self.units)

    def fragment_count(self) -> int:
        return sum(len(u.fragments) for u in self.units)
