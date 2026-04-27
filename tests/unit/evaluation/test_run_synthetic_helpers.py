"""Tests for pure helper functions in the synthetic evaluation runner."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from reconstructor.core.architecture import Architecture
from reconstructor.core.chain import DecisionChain, DecisionUnit
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.evaluation.synthetic_console import _print_tables
from reconstructor.evaluation.synthetic_evaluation import _scenario_row, _SyntheticEvaluation
from reconstructor.evaluation.synthetic_outputs import (
    _build_outputs,
    _cell_rows,
    _per_property_summary,
    _SyntheticOutputs,
    _write_outputs,
)
from reconstructor.mapping.operational_modes import OperationalMode
from reconstructor.pipeline import ReconstructionReport
from reconstructor.synthetic.generator import Scenario


def _fragment() -> Fragment:
    return Fragment(
        fragment_id="f0",
        timestamp=1.0,
        kind=FragmentKind.AGENT_MESSAGE,
        stack_tier=StackTier.WITHIN_STACK,
        actor_id="agent",
        payload={"content": "hello"},
    )


def _report() -> ReconstructionReport:
    fragment = _fragment()
    unit = DecisionUnit(
        unit_id="u0",
        fragments=[fragment],
        boundary_reason="tool_call",
        boundary_confidence=0.8,
    )
    chain = DecisionChain(chain_id="chain", units=[unit], source_fragments=[fragment])
    return ReconstructionReport(
        chain_id="chain",
        architecture=Architecture.MULTI_AGENT,
        stack_tier=StackTier.CROSS_STACK,
        chain=chain,
        per_unit_feasibility={},
        completeness=0.5,
        total_property_slots=7,
        unrecoverable_modes=[OperationalMode.MODE_5_DELEGATION_CHAIN],
    )


def test_scenario_row_serializes_report_summary() -> None:
    scenario = Scenario(
        scenario_id="scenario",
        architecture=Architecture.MULTI_AGENT,
        stack_tier=StackTier.CROSS_STACK,
        seed=42,
        fragments=[_fragment()],
        ground_truth_boundaries=[],
    )
    row = _scenario_row(scenario, _report(), f1=0.75)
    assert row == {
        "scenario_id": "scenario",
        "architecture": "multi_agent",
        "stack_tier": "cross_stack",
        "seed": 42,
        "fragments": 1,
        "units_detected": 1,
        "completeness": 0.5,
        "boundary_f1": 0.75,
        "unrecoverable_mode_count": 1,
        "dominant_mode": 5,
        "dominant_break": "decision_diffusion",
    }


def test_per_property_summary_fills_all_categories() -> None:
    counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    counts["inputs"]["fully_fillable"] = 3
    counts["inputs"]["opaque"] = 1
    summary = _per_property_summary(counts)
    assert summary["inputs"]["fully_fillable"] == 75.0
    assert summary["inputs"]["opaque"] == 25.0
    assert summary["inputs"]["partially_fillable"] == 0.0
    assert summary["inputs"]["structurally_unfillable"] == 0.0


def test_cell_rows_aggregate_evaluation_buckets() -> None:
    evaluation = _SyntheticEvaluation()
    evaluation.per_cell_completeness[("multi_agent", "cross_stack")].extend([0.25, 0.75])
    evaluation.per_cell_f1[("multi_agent", "cross_stack")].extend([0.5, 1.0])
    evaluation.per_cell_modes[("multi_agent", "cross_stack")].append(
        [OperationalMode.MODE_5_DELEGATION_CHAIN]
    )
    rows = _cell_rows(evaluation)
    assert rows == [
        {
            "architecture": "multi_agent",
            "stack_tier": "cross_stack",
            "n": 2,
            "completeness_pct": 50.0,
            "completeness_ci_low": 25.0,
            "completeness_ci_high": 75.0,
            "boundary_f1": 0.75,
            "modal_mode": 5,
            "modal_mode_share": 1.0,
            "dominant_break": "decision_diffusion",
        }
    ]


def test_build_outputs_and_write_outputs(tmp_path: Path) -> None:
    evaluation = _SyntheticEvaluation()
    evaluation.per_cell_completeness[("single_agent", "within_stack")].append(1.0)
    evaluation.per_cell_f1[("single_agent", "within_stack")].append(1.0)
    evaluation.per_scenario_rows.append(
        {
            "scenario_id": "s1",
            "architecture": "single_agent",
            "stack_tier": "within_stack",
            "seed": 1,
            "fragments": 1,
            "units_detected": 1,
            "completeness": 1.0,
            "boundary_f1": 1.0,
            "unrecoverable_mode_count": 0,
            "dominant_mode": None,
            "dominant_break": None,
        }
    )
    evaluation.per_property_counts["inputs"]["fully_fillable"] = 1

    outputs = _build_outputs(evaluation)
    assert outputs.cells[0]["architecture"] == "single_agent"
    assert outputs.per_property_summary["inputs"]["fully_fillable"] == 100.0

    _write_outputs(tmp_path, outputs)
    assert (tmp_path / "per_scenario.json").exists()
    assert (tmp_path / "per_scenario.jsonld").exists()
    assert (tmp_path / "cells.json").exists()
    assert (tmp_path / "cells.jsonld").exists()
    assert (tmp_path / "per_property.json").exists()


def test_print_tables_handles_missing_cells(capsys) -> None:  # type: ignore[no-untyped-def]
    outputs = _SyntheticOutputs(
        cells=[
            {
                "architecture": "single_agent",
                "stack_tier": "within_stack",
                "n": 1,
                "completeness_pct": 100.0,
                "completeness_ci_low": 100.0,
                "completeness_ci_high": 100.0,
                "boundary_f1": 1.0,
                "modal_mode": None,
                "modal_mode_share": 0.0,
                "dominant_break": None,
            }
        ],
        per_property_summary={
            "inputs": {
                "fully_fillable": 100.0,
                "partially_fillable": 0.0,
                "structurally_unfillable": 0.0,
                "opaque": 0.0,
            }
        },
        per_scenario_rows=[],
    )
    _print_tables(outputs.cells, outputs.per_property_summary)
    captured = capsys.readouterr()
    assert "Table 4." in captured.out
    assert "Table 5." in captured.out
    assert "Table 6." in captured.out
    assert "Table 8." in captured.out
