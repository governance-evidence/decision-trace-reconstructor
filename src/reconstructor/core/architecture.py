"""Architecture labels used by reconstruction and evaluation."""

from __future__ import annotations

from enum import Enum


class Architecture(str, Enum):
    """Supported decision-chain architecture profiles."""

    SINGLE_AGENT = "single_agent"
    MULTI_AGENT = "multi_agent"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    NON_AGENTIC = "non_agentic"


AGENTIC_ARCHITECTURES: tuple[Architecture, ...] = (
    Architecture.SINGLE_AGENT,
    Architecture.MULTI_AGENT,
    Architecture.HUMAN_IN_THE_LOOP,
)


def coerce_architecture(value: Architecture | str) -> Architecture:
    """Normalise a user- or adapter-supplied architecture label."""
    if isinstance(value, Architecture):
        return value
    try:
        return Architecture(str(value))
    except ValueError as exc:
        valid = ", ".join(arch.value for arch in Architecture)
        raise ValueError(f"unknown architecture {value!r}. Expected one of: {valid}") from exc
