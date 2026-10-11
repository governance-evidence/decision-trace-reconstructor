"""Regression coverage for v2 evidence boundaries and irreversible inference costs."""

import json
from copy import deepcopy

import pytest

from experiments.paper23.storage import read, write
from experiments.paper23_assessor_v2.client import Client
from experiments.paper23_assessor_v2.controls import controls
from experiments.paper23_assessor_v2.rubric import (
    OBLIGATIONS,
    admissibility,
    model_view,
    project,
    validate,
)
from experiments.paper23_assessor_v2.runner import assess_one, run_main


def answer(packet):
    by_kind = {r["kind"]: r["id"] for r in packet["records"]}
    slots = {
        "Q1": {
            "principal_identity": [by_kind["authority"]],
            "acting_roles": [by_kind["tool_request"]],
        },
        "Q2": {
            "delegation": [by_kind["authority"]],
            "scope": [by_kind["authority"]],
            "human_decisions": [],
        },
        "Q3": {
            "request": [by_kind["prompt"]],
            "pre_action_information": [
                next(
                    r["id"]
                    for r in packet["records"]
                    if r["kind"] == "service_receipt" and r["data"].get("phase") == "before"
                )
            ],
        },
        "Q4": {"policy_version": [by_kind["policy"]], "applicable_rule": [by_kind["policy"]]},
        "Q5": {"tools_resources": [by_kind["configuration"]], "preconditions": [by_kind["policy"]]},
        "Q6": {
            "issued_actions": [by_kind["tool_request"]],
            "parameters": [by_kind["tool_request"]],
        },
        "Q7": {
            "execution_receipts": [by_kind["service_receipt"]],
            "final_state": [by_kind["final_state_check"]],
        },
    }
    return {
        "questions": {
            q: {
                "label": "fully_supported",
                "answer": "Observed fact",
                "evidence": slots[q],
                "missing": [],
                "contradictions": [],
                "reason": "Evidence linked",
            }
            for q in OBLIGATIONS
        }
    }


def test_projection_preserves_original_and_removes_only_oracle_fields():
    packet = controls()[0]["packet"]
    state = next(r for r in packet["records"] if r["kind"] == "final_state_check")
    state["data"].update(expected_disposition="committed", state_matches_expected=True)
    before = deepcopy(packet)
    view, removed = project(packet)
    assert packet == before
    assert {x["field"] for x in removed} == {"expected_disposition", "state_matches_expected"}
    for x in removed:
        original = next(r for r in before["records"] if r["id"] == x["record_id"])
        del original["data"][x["field"]]
    assert view == before
    assert set(model_view(view)) == {"packet_id", "records"}


def test_role_and_temporal_flags_preserve_raw_label():
    packet = controls()[0]["packet"]
    value = answer(packet)
    assert validate(value, packet) == value
    assert not admissibility(value, packet)
    state = next(r for r in packet["records"] if r["kind"] == "final_state_check")
    state["time"] = 6.5
    assert any(
        x["issue"] == "state_predates_execution_receipt" for x in admissibility(value, packet)
    )
    value["questions"]["Q7"]["evidence"]["execution_receipts"] = [
        next(r["id"] for r in packet["records"] if r["kind"] == "tool_request")
    ]
    assert any(x["issue"] == "inadmissible_execution_receipt" for x in admissibility(value, packet))
    assert value["questions"]["Q7"]["label"] == "fully_supported"


def test_control_population_includes_positive_human_and_keeps_expectations_private():
    cases = controls()
    assert len(cases) == 10
    assert len({c["packet"]["packet_id"] for c in cases}) == 10
    human = next(c for c in cases if c["name"] == "documented_human_two_attempts")
    assert len([r for r in human["packet"]["records"] if r["kind"] == "human_decision"]) == 2
    assert human["expected"] == {q: ["fully_supported"] for q in ("Q2", "Q6", "Q7")}
    assert "expected" not in model_view(human["packet"])
    assert "name" not in model_view(human["packet"])


def test_one_structural_correction_no_semantic_repair_and_no_requery(tmp_path):
    packet = controls()[0]["packet"]
    write(tmp_path / "packets/controls" / f"{packet['packet_id']}.json", packet)
    value = answer(packet)
    value["questions"]["Q7"]["evidence"]["execution_receipts"] = [
        next(r["id"] for r in packet["records"] if r["kind"] == "tool_request")
    ]
    malformed = deepcopy(value)
    malformed["questions"]["Q1"]["evidence"]["acting_roles"] = ["absent-id"]

    class Fake:
        calls = []

        def complete(self, run_id, messages):
            self.calls.append(deepcopy(messages))
            data = malformed if len(self.calls) == 1 else value
            return {
                "choices": [{"message": {"content": json.dumps(data)}, "finish_reason": "stop"}]
            }, str(len(self.calls))

    client = Fake()
    audit = assess_one(tmp_path, "controls", packet["packet_id"], client)
    assert len(client.calls) == 2
    assert audit["status"] == "complete"
    assert audit["admissibility_flags"]
    assert audit["assessment"] == value
    assert "schema or packet-ID error" in client.calls[1][-1]["content"]
    assert assess_one(tmp_path, "controls", packet["packet_id"], client) == audit
    assert len(client.calls) == 2


def test_failed_control_gate_blocks_main_without_inference(tmp_path, monkeypatch):
    monkeypatch.setattr("experiments.paper23_assessor_v2.runner.verify_freeze", lambda root: None)
    write(tmp_path / "control-gate.json", {"passed": False})

    class Fail:
        def complete(self, *args):
            raise AssertionError("No main inference permitted")

    with pytest.raises(ValueError, match="Control gate failed"):
        run_main(tmp_path, Fail())


def test_aggregate_budget_includes_prior_run_before_network(tmp_path):
    write(
        tmp_path / "budget.json",
        {
            "cap_usd": 5.0,
            "requests": [{"id": "prior", "state": "settled", "charged_or_reserved_usd": 4.99}],
        },
    )

    def fail(*args):
        raise AssertionError("Reservation must stop before network")

    client = Client(tmp_path, "unused", send=fail)
    with pytest.raises(RuntimeError, match="cap"):
        client.complete("test", [{"role": "user", "content": "test"}])
    assert len(read(tmp_path / "budget.json")["requests"]) == 1


def test_all_positive_or_all_negative_judge_cannot_pass_controls(tmp_path, monkeypatch):
    from experiments.paper23_assessor_v2.runner import run_controls

    monkeypatch.setattr("experiments.paper23_assessor_v2.runner.verify_freeze", lambda root: None)
    cases = [
        {k: v for k, v in c.items() if k != "packet"} | {"packet_id": c["packet"]["packet_id"]}
        for c in controls()
    ]
    for label in ("fully_supported", "unsupported"):
        root = tmp_path / label
        write(root / "control-expectations.json", cases)

        def fake(*args, current_label=label):
            return {
                "status": "complete",
                "admissibility_flags": [],
                "assessment": {"questions": {q: {"label": current_label} for q in OBLIGATIONS}},
            }

        monkeypatch.setattr("experiments.paper23_assessor_v2.runner.assess_one", fake)
        assert run_controls(root, object())["passed"] is False
