"""Synthetic scenario generator facade.

Produces deterministic-given-seed scenarios across the 3x2 matrix of
architectures and stack-coverage tiers plus a non-agentic baseline.
Each scenario is a list of Fragments plus metadata
(architecture, stack_tier, ground_truth_boundaries).

Determinism is strict: same seed -> bit-for-bit identical scenario, and
``_stable_seed`` is independent of PYTHONHASHSEED (which randomises
Python's built-in ``hash()`` for strings across processes). The seed
function is rooted in SHA-256 so the same (architecture, tier, index)
triple yields the same integer seed across hosts, Python versions, and
process invocations.
"""

from __future__ import annotations

import hashlib

from ..core.architecture import AGENTIC_ARCHITECTURES
from ..core.fragment import StackTier
from .agentic_generator import _make_fragment, generate_scenario
from .baseline_generator import _append_baseline_fragment, _non_agentic_baseline
from .scenario import Scenario

ARCHITECTURES = AGENTIC_ARCHITECTURES
STACK_TIERS: tuple[StackTier, ...] = (StackTier.WITHIN_STACK, StackTier.CROSS_STACK)


def generate_matrix(seeds_per_cell: int = 20) -> list[Scenario]:
    """Generate the full 3x2 matrix plus non-agentic baseline scenarios.

    Returns (3 architectures x 2 stack tiers x seeds_per_cell) + seeds_per_cell baseline.
    """
    scenarios: list[Scenario] = []
    for arch in ARCHITECTURES:
        for tier in STACK_TIERS:
            for k in range(seeds_per_cell):
                seed = _stable_seed(arch.value, tier.value, k)
                scenarios.append(generate_scenario(arch, tier, seed))
    for k in range(seeds_per_cell):
        seed = _stable_seed("non_agentic", "baseline", k)
        scenarios.append(_non_agentic_baseline(seed))
    return scenarios


def _stable_seed(arch: str, tier: str, k: int) -> int:
    """Deterministic seed from (architecture, tier, index).

    Uses SHA-256 rather than Python's built-in ``hash()`` to defeat
    PYTHONHASHSEED string-hash randomisation. The result is a positive
    31-bit integer (range 0..0x7FFFFFFF) and is identical across hosts,
    Python versions, and process invocations for the same input triple.
    """
    digest = hashlib.sha256(f"{arch}|{tier}|{k}".encode()).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


__all__ = [
    "ARCHITECTURES",
    "STACK_TIERS",
    "Scenario",
    "_append_baseline_fragment",
    "_make_fragment",
    "_non_agentic_baseline",
    "_stable_seed",
    "generate_matrix",
    "generate_scenario",
]
