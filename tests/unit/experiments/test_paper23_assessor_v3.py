"""Fixed hybrid aggregation and retained obligation evidence, before v3 inference."""

from copy import deepcopy

import pytest

from experiments.paper23_assessor_v2.controls import controls as prior_controls
from experiments.paper23_assessor_v3.controls import controls
from experiments.paper23_assessor_v3.rubric import (
    OBLIGATIONS,
    admissibility,
    aggregate,
    derive,
    validate,
)


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["supported", "supported"], "fully_supported"),
        (["supported", "not_required"], "fully_supported"),
        (["missing", "missing", "not_required"], "unsupported"),
        (["supported", "missing"], "partially_supported"),
        (["partial", "missing"], "partially_supported"),
        (["supported", "partial"], "partially_supported"),
        (["supported", "contradictory"], "contradictory"),
        (["missing", "contradictory", "not_required"], "contradictory"),
    ],
)
def test_aggregation_truth_table(statuses, expected):
    assert aggregate(statuses) == expected


def test_vacuous_aggregation_rejected():
    with pytest.raises(ValueError):
        aggregate(["not_required"])


def blank():
    return {
        "questions": {
            q: {
                "answer": "Not established",
                "evidence": {s: [] for s in slots},
                "statuses": {s: "missing" for s in slots},
                "contradictions": [],
                "reason": "Absent evidence",
            }
            for q, slots in OBLIGATIONS.items()
        }
    }


def test_derived_reference_preserves_raw_and_delegated_scope_cannot_use_config():
    packet = controls()[0]["packet"]
    raw = blank()
    before = deepcopy(raw)
    assert validate(raw, packet) == raw
    derived = derive(raw)
    assert raw == before
    assert all(q["label"] == "unsupported" for q in derived["questions"].values())
    config = next(r["id"] for r in packet["records"] if r["kind"] == "configuration")
    raw["questions"]["Q2"]["evidence"]["delegated_scope"] = [config]
    raw["questions"]["Q2"]["statuses"]["delegated_scope"] = "partial"
    assert any(f["issue"] == "no_authority_record" for f in admissibility(derive(raw), packet))
    assert raw["questions"]["Q2"]["statuses"]["delegated_scope"] == "partial"


def test_not_required_needs_explicit_false_gate_and_is_field_limited():
    packet = controls()[0]["packet"]
    raw = blank()
    raw["questions"]["Q2"]["statuses"]["human_decisions"] = "not_required"
    assert any(f["issue"] == "invalid_not_required" for f in admissibility(derive(raw), packet))
    config = next(r["id"] for r in packet["records"] if r["kind"] == "configuration")
    raw["questions"]["Q2"]["evidence"]["human_decisions"] = [config]
    assert not any(f["issue"] == "invalid_not_required" for f in admissibility(derive(raw), packet))
    raw["questions"]["Q7"]["statuses"]["final_state"] = "not_required"
    with pytest.raises(ValueError, match="not_required"):
        validate(raw, packet)


def test_fresh_control_instances_retain_positive_negative_archetypes():
    new = controls()
    old = prior_controls()
    assert len(new) == 10
    assert {x["name"] for x in new} == {x["name"] for x in old}
    assert not (
        {r["id"] for c in new for r in c["packet"]["records"]}
        & {r["id"] for c in old for r in c["packet"]["records"]}
    )
    assert all("switch-x" not in str(x["packet"]) for x in new)
    assert all(
        x["expected"] == next(y["expected"] for y in old if y["name"] == x["name"]) for x in new
    )


def test_supported_components_checked_even_when_question_is_partial():
    packet = next(c["packet"] for c in controls() if c["name"] == "documented_human_two_attempts")
    raw = blank()
    receipts = [
        r
        for r in packet["records"]
        if r["kind"] == "service_receipt" and r["data"].get("phase") != "before"
    ]
    approvals = [r for r in packet["records"] if r["kind"] == "human_decision"]
    raw["questions"]["Q7"]["statuses"]["execution_receipts"] = "supported"
    raw["questions"]["Q7"]["evidence"]["execution_receipts"] = [receipts[0]["id"]]
    raw["questions"]["Q2"]["statuses"]["human_decisions"] = "supported"
    raw["questions"]["Q2"]["evidence"]["human_decisions"] = [approvals[0]["id"]]
    derived = derive(raw)
    assert derived["questions"]["Q7"]["label"] == "partially_supported"
    assert derived["questions"]["Q2"]["label"] == "partially_supported"
    issues = {f["issue"] for f in admissibility(derived, packet)}
    assert "unmatched_execution_receipt" in issues
    assert "unmatched_human_decision" in issues
    assert raw["questions"]["Q7"]["statuses"]["execution_receipts"] == "supported"
