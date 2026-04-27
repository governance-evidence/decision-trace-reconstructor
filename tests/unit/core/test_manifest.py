"""Fragment manifest wire-format tests."""

from __future__ import annotations

import pytest

from reconstructor.core.architecture import Architecture
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.core.manifest import FragmentManifest, manifest_dict


def _fragment() -> Fragment:
    return Fragment(
        fragment_id="f1",
        timestamp=1.0,
        kind=FragmentKind.AGENT_MESSAGE,
        stack_tier=StackTier.WITHIN_STACK,
        actor_id="agent",
        payload={"content": "hello"},
    )


def test_fragment_manifest_round_trips_wire_dict() -> None:
    manifest = FragmentManifest(
        scenario_id="scenario",
        architecture=Architecture.SINGLE_AGENT,
        stack_tier=StackTier.WITHIN_STACK,
        fragments=[_fragment()],
    )

    assert FragmentManifest.from_dict(manifest.to_dict()) == manifest


def test_manifest_dict_keeps_legacy_adapter_shape() -> None:
    payload = manifest_dict(
        scenario_id="scenario",
        architecture=Architecture.SINGLE_AGENT,
        stack_tier=StackTier.WITHIN_STACK,
        fragments=[_fragment()],
    )

    assert payload == {
        "scenario_id": "scenario",
        "architecture": "single_agent",
        "stack_tier": "within_stack",
        "fragments": [_fragment().to_dict()],
    }


def test_fragment_manifest_requires_manifest_keys() -> None:
    with pytest.raises(KeyError, match="missing required key 'stack_tier'"):
        FragmentManifest.from_dict(
            {
                "scenario_id": "scenario",
                "architecture": "single_agent",
                "fragments": [],
            }
        )
