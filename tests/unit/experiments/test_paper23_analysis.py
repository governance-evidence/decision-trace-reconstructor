"""Agreement metrics are reference-relative and cannot invent human evidence."""

import pytest

from experiments.paper23.packets import QUESTIONS
from experiments.paper23_analysis.judge import validate
from experiments.paper23_analysis.scoring import metrics, paired, references


def row(reference, prediction, condition="full", excluded=False):
    return {
        "run_id": "r",
        "property": "inputs",
        "reference": reference,
        "dtr": prediction,
        "condition": condition,
        "excluded": excluded,
    }


def test_metrics_keep_actual_denominators_and_processing_failures():
    rows = [
        row("fully_supported", "fully_fillable"),
        row("unsupported", "fully_fillable"),
        row("fully_supported", "processing_failure"),
        row("contradictory", "partially_fillable"),
        row("fully_supported", "fully_fillable", excluded=True),
    ]
    result = metrics(rows)
    assert result["assessable"] == 4 and result["excluded"] == 1
    assert result["false_sufficient_fraction_relative_to_ai"]["value"] == 0.5
    assert result["missed_sufficiency_fraction_relative_to_ai"]["value"] == 0.5
    assert result["processing_failures"] == 1
    assert any(r["reference"] == "contradictory" for r in result["confusion"])


def test_empty_denominators_are_na():
    result = metrics([row("unsupported", "structurally_unfillable")])
    assert result["precision_relative_to_ai"]["value"] is None
    assert result["recall_relative_to_ai"]["value"] is None


def test_paired_sensitivity_does_not_assume_all_deletions_change_support():
    rows = [row("fully_supported", "fully_fillable"), row("unsupported", "partially_fillable", "A")]
    assert paired(rows)["deletion_sensitivity_relative_to_ai"]["value"] == 1
    rows[1]["reference"] = "fully_supported"
    result = paired(rows)
    assert result["deletion_sensitivity_relative_to_ai"]["denominator"] == 0
    assert result["unjustified_downgrades_relative_to_ai"]["value"] == 1


def test_judge_cannot_cite_the_hidden_ledger():
    answers = {
        q: {"label": "fully_supported", "answer": "A", "reason": "R", "evidence_ids": ["hidden"]}
        for q in QUESTIONS
    }
    with pytest.raises(ValueError, match="outside packet"):
        validate({"questions": answers}, {"records": [{"id": "visible"}]})


def test_missing_frozen_labels_block_before_dtr_execution(tmp_path):
    with pytest.raises(FileNotFoundError):
        references(tmp_path, "main")
