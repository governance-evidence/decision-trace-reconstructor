"""CLI tests for ``decision-trace reconstruct``."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main
from reconstructor.core.architecture import Architecture
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.core.manifest import FragmentManifest


def _fragment(
    fragment_id: str,
    timestamp: float,
    kind: FragmentKind,
    payload: dict[str, object],
    actor_id: str = "agent",
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=kind,
        stack_tier=StackTier.WITHIN_STACK,
        actor_id=actor_id,
        payload=payload,
    )


def _manifest() -> FragmentManifest:
    return FragmentManifest(
        scenario_id="cli_reconstruct",
        architecture=Architecture.SINGLE_AGENT,
        stack_tier=StackTier.WITHIN_STACK,
        fragments=[
            _fragment("f1", 1.0, FragmentKind.AGENT_MESSAGE, {"content": "summarize account"}),
            _fragment("f2", 2.0, FragmentKind.POLICY_SNAPSHOT, {"policy_id": "p1"}),
            _fragment("f3", 3.0, FragmentKind.CONFIG_SNAPSHOT, {"model": "test-model"}),
            _fragment("f4", 4.0, FragmentKind.MODEL_GENERATION, {"output": "draft"}),
            _fragment("f5", 5.0, FragmentKind.TOOL_CALL, {"tool_name": "write_report"}),
            _fragment("f6", 6.0, FragmentKind.STATE_MUTATION, {"path": "report.md"}),
        ],
    )


def test_reconstruct_cli_writes_feasibility_and_jsonld(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    input_path = tmp_path / "fragments.json"
    out_dir = tmp_path / "report"
    input_path.write_text(_manifest().to_json())

    exit_code = main(["reconstruct", str(input_path), "--out", str(out_dir), "--jsonld"])

    assert exit_code == 0
    feasibility = json.loads((out_dir / "feasibility.json").read_text())
    trace = json.loads((out_dir / "trace.jsonld").read_text())
    assert feasibility["scenario_id"] == "cli_reconstruct"
    assert feasibility["fragments"] == 6
    assert feasibility["feasibility_counts"]["fully_fillable"] >= 5
    assert any(item["category"] == "opaque" for item in feasibility["per_property"])
    assert trace["@context"]
    assert trace["@graph"][0]["demm:scenarioId"] == "cli_reconstruct"

    captured = capsys.readouterr()
    assert "reconstructed cli_reconstruct" in captured.out
    assert "outputs:" in captured.out


def test_reconstruct_cli_can_write_only_feasibility_json(tmp_path: Path) -> None:
    input_path = tmp_path / "fragments.json"
    out_dir = tmp_path / "report"
    input_path.write_text(_manifest().to_json())

    exit_code = main(["reconstruct", str(input_path), "--out", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "feasibility.json").exists()
    assert not (out_dir / "trace.jsonld").exists()


def test_reconstruct_cli_reports_manifest_validation_error(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    input_path = tmp_path / "bad_fragments.json"
    input_path.write_text(json.dumps({"scenario_id": "broken", "architecture": "single_agent"}))

    exit_code = main(["reconstruct", str(input_path), "--out", str(tmp_path / "report")])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "input manifest missing required key 'stack_tier'" in captured.err
