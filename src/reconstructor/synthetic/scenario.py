"""Synthetic scenario data model."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.architecture import Architecture, coerce_architecture
from ..core.fragment import Fragment, StackTier


@dataclass
class Scenario:
    """A synthetic agent decision chain with ground truth."""

    scenario_id: str
    architecture: Architecture
    stack_tier: StackTier
    seed: int
    fragments: list[Fragment]
    ground_truth_boundaries: list[int]  # indices in fragments where boundaries should be

    def __post_init__(self) -> None:
        self.architecture = coerce_architecture(self.architecture)
