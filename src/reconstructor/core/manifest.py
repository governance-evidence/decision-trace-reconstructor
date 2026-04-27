"""Typed fragment manifest boundary.

Adapters and examples expose manifests as JSON dictionaries for CLI
compatibility. Internally, use ``FragmentManifest`` so the wire shape is owned
by one module instead of being hand-built in every adapter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .architecture import Architecture, coerce_architecture
from .fragment import Fragment, StackTier


@dataclass(frozen=True)
class FragmentManifest:
    """A complete fragment manifest consumed by ``decision-trace reconstruct``."""

    scenario_id: str
    architecture: Architecture
    stack_tier: StackTier
    fragments: list[Fragment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "architecture", coerce_architecture(self.architecture))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FragmentManifest:
        """Construct a manifest from the JSON wire shape."""
        _require_manifest_keys(data)
        return cls(
            scenario_id=str(data["scenario_id"]),
            architecture=coerce_architecture(data["architecture"]),
            stack_tier=StackTier(data["stack_tier"]),
            fragments=[Fragment.from_dict(fragment) for fragment in data["fragments"]],
        )

    @classmethod
    def from_json(cls, path: str | Path) -> FragmentManifest:
        """Load a manifest from a JSON file."""
        return cls.from_dict(json.loads(Path(path).read_text()))

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the stable JSON wire shape."""
        return {
            "scenario_id": self.scenario_id,
            "architecture": self.architecture.value,
            "stack_tier": self.stack_tier.value,
            "fragments": [fragment.to_dict() for fragment in self.fragments],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent) + "\n"

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json())


def manifest_dict(
    *,
    scenario_id: str,
    architecture: Architecture | str,
    stack_tier: StackTier,
    fragments: list[Fragment],
) -> dict[str, Any]:
    """Build a legacy manifest dict through the typed manifest boundary."""
    return FragmentManifest(
        scenario_id=scenario_id,
        architecture=coerce_architecture(architecture),
        stack_tier=stack_tier,
        fragments=fragments,
    ).to_dict()


def _require_manifest_keys(data: dict[str, Any]) -> None:
    required = ("scenario_id", "architecture", "stack_tier", "fragments")
    for key in required:
        if key not in data:
            raise KeyError(f"FragmentManifest.from_dict: missing required key {key!r}")
