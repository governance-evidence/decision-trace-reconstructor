"""Fast entrypoint tests for evaluation runners."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reconstructor.core.architecture import Architecture
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.evaluation import run_named, run_synthetic
from reconstructor.synthetic.generator import Scenario


def _scenario(scenario_id: str = "synthetic_one") -> Scenario:
    fragments = [
        Fragment(
            fragment_id="f1",
            timestamp=1.0,
            kind=FragmentKind.AGENT_MESSAGE,
            stack_tier=StackTier.WITHIN_STACK,
            actor_id="agent",
            payload={"content": "inspect"},
        ),
        Fragment(
            fragment_id="f2",
            timestamp=2.0,
            kind=FragmentKind.MODEL_GENERATION,
            stack_tier=StackTier.WITHIN_STACK,
            actor_id="agent",
            payload={"output": "plan"},
        ),
        Fragment(
            fragment_id="f3",
            timestamp=3.0,
            kind=FragmentKind.TOOL_CALL,
            stack_tier=StackTier.WITHIN_STACK,
            actor_id="agent",
            payload={"tool_name": "write"},
        ),
    ]
    return Scenario(
        scenario_id=scenario_id,
        architecture=Architecture.SINGLE_AGENT,
        stack_tier=StackTier.WITHIN_STACK,
        seed=123,
        fragments=fragments,
        ground_truth_boundaries=[2],
    )


def test_run_synthetic_main_writes_artifacts_for_generated_scenarios(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(run_synthetic, "generate_matrix", lambda seeds_per_cell: [_scenario()])

    exit_code = run_synthetic.main(["--seeds-per-cell", "1", "--out", str(tmp_path)])

    assert exit_code == 0
    assert (
        json.loads((tmp_path / "per_scenario.json").read_text())[0]["scenario_id"]
        == "synthetic_one"
    )
    assert (tmp_path / "per_scenario.jsonld").exists()
    assert (tmp_path / "cells.json").exists()
    assert (tmp_path / "cells.jsonld").exists()
    assert (tmp_path / "per_property.json").exists()
    assert "Generated 1 scenarios" in capsys.readouterr().out


def test_run_named_main_writes_summary_and_jsonld_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(run_named, "all_named_incidents", lambda: [_scenario("named_one")])

    exit_code = run_named.main(["--out", str(tmp_path)])

    assert exit_code == 0
    rows = json.loads((tmp_path / "named_incidents.json").read_text())
    bundle = json.loads((tmp_path / "named_incidents.jsonld").read_text())
    assert rows[0]["incident"] == "named_one"
    assert rows[0]["feasibility_counts"]["opaque"] == 1
    assert bundle["@graph"][0]["demm:scenarioId"] == "named_one"
    assert "Table 7." in capsys.readouterr().out
