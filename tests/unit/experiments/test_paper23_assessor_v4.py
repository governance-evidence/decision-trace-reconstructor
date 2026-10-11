"""Failure-specific regressions and adversarial protection of frozen inference."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from experiments.paper23.storage import digest, read, write
from experiments.paper23_assessor_v3.controls import controls
from experiments.paper23_assessor_v3.rubric import OBLIGATIONS, derive
from experiments.paper23_assessor_v4 import runner
from experiments.paper23_assessor_v4.rubric import status_snapshot, validate


def blank():
    return {
        "questions": {
            q: {
                "answer": "Not established",
                "reason": "Missing evidence",
                "evidence": {s: [] for s in slots},
                "statuses": {s: "missing" for s in slots},
                "contradictions": [],
            }
            for q, slots in OBLIGATIONS.items()
        }
    }


def test_receipt_in_missing_final_slot_refuses_without_relabelling():
    packet = next(c["packet"] for c in controls() if c["name"] == "receipt_only")
    value = blank()
    receipt = next(
        r["id"]
        for r in packet["records"]
        if r["kind"] == "service_receipt" and r["data"].get("status") == "committed"
    )
    value["questions"]["Q7"]["evidence"]["final_state"] = [receipt]
    saved = deepcopy(value)
    with pytest.raises(ValueError, match="missing status requires an empty"):
        validate(value, packet)
    assert value == saved


def test_conflict_ids_not_prose_and_distinct_pair_required():
    packet = next(c["packet"] for c in controls() if c["name"] == "unresolved_state_conflict")
    states = [r["id"] for r in packet["records"] if r["kind"] == "final_state_check"]
    value = blank()
    q = value["questions"]["Q7"]
    q["statuses"]["final_state"] = "contradictory"
    q["evidence"]["final_state"] = states
    q["contradictions"] = ["These two final states disagree"]
    with pytest.raises(ValueError, match="packet-local IDs"):
        validate(value, packet)
    q["contradictions"] = states
    validate(value, packet)
    assert derive(value)["questions"]["Q7"]["label"] == "contradictory"
    q["contradictions"] = [states[0], states[0]]
    with pytest.raises(ValueError, match="distinct"):
        validate(value, packet)


def test_correction_cannot_change_status_to_pass():
    packet = controls()[0]["packet"]
    value = blank()
    locked = status_snapshot(value)
    value["questions"]["Q7"]["statuses"]["final_state"] = "supported"
    value["questions"]["Q7"]["evidence"]["final_state"] = [
        next(r["id"] for r in packet["records"] if r["kind"] == "final_state_check")
    ]
    with pytest.raises(ValueError, match="locked obligation status"):
        validate(value, packet, locked)


@pytest.mark.parametrize("value", [None, [], {}, {"questions": []}, {"questions": None}])
def test_malformed_root_is_controlled_error(value):
    with pytest.raises(ValueError):
        validate(value, controls()[0]["packet"])


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, run_id, messages):
        self.calls.append(deepcopy(messages))
        return {
            "choices": [{"message": {"content": next(self.responses)}, "finish_reason": "stop"}]
        }, str(len(self.calls))


def setup_packet(tmp_path):
    packet = next(c["packet"] for c in controls() if c["name"] == "receipt_only")
    write(tmp_path / "packets/controls" / (packet["packet_id"] + ".json"), packet)
    value = blank()
    invalid = deepcopy(value)
    invalid["questions"]["Q7"]["evidence"]["final_state"] = [packet["records"][0]["id"]]
    return packet, value, invalid


def test_correction_keeps_both_responses_and_statuses(tmp_path):
    packet, value, invalid = setup_packet(tmp_path)
    client = FakeClient([json.dumps(invalid), json.dumps(value)])
    audit = runner.assess_one(tmp_path, "controls", packet["packet_id"], client)
    assert audit["status"] == "complete"
    assert len(audit["responses"]) == 2
    assert audit["responses"][0]["normalization"]["parsed"] == invalid
    assert audit["raw_assessment"] == value
    assert audit["locked_statuses"] == status_snapshot(invalid)
    assert "expected" not in client.calls[1][-1]["content"]
    assert runner.replay_assessment(audit, packet) == audit
    runner.assess_one(tmp_path, "controls", packet["packet_id"], client)
    assert len(client.calls) == 2


def test_invalid_second_response_is_terminal(tmp_path):
    packet, value, invalid = setup_packet(tmp_path)
    client = FakeClient([json.dumps(invalid), "The schema has been corrected."])
    audit = runner.assess_one(tmp_path, "controls", packet["packet_id"], client)
    assert audit["status"] == "invalid_assessment"
    assert len(client.calls) == 2
    assert runner.replay_assessment(audit, packet) == audit


def test_failed_controls_block_main_before_any_call(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify_freeze", lambda root: None)
    monkeypatch.setattr(runner, "verify_control_gate", lambda root: {"passed": False})
    client = FakeClient([])
    with pytest.raises(ValueError, match="Control gate failed"):
        runner.run_main(tmp_path, client)
    assert client.calls == []


def test_changed_derived_label_refused_on_replay(tmp_path):
    packet, value, invalid = setup_packet(tmp_path)
    audit = runner.assess_one(
        tmp_path, "controls", packet["packet_id"], FakeClient([json.dumps(value)])
    )
    audit["assessment"]["questions"]["Q7"]["label"] = "fully_supported"
    with pytest.raises(ValueError, match="differs from raw response"):
        runner.replay_assessment(audit, packet)


def test_recorded_v3_failures_are_detected():
    root = Path(__file__).resolve().parents[3] / "study-data/paper23-20261010-assessor-v3"
    if not root.exists():
        pytest.skip("Local retained V3 study not distributed in source checkout")
    for packet_id in ["ee451b11f895bd0b", "d99a02126aa48119"]:
        audit = read(root / "assessments/controls" / (packet_id + ".json"))
        packet = read(root / "packets/controls" / (packet_id + ".json"))
        from experiments.paper23_assessor_v2_normalization import extract

        raw, _ = extract(audit["responses"][0]["content"])
        before = digest(raw)
        with pytest.raises(ValueError):
            validate(raw, packet)
        assert digest(raw) == before


def test_forged_passing_gate_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify_freeze", lambda root: None)
    cases = controls()
    entries = []
    results = []
    for case in cases:
        packet = case["packet"]
        packet_id = packet["packet_id"]
        write(tmp_path / "packets/controls" / (packet_id + ".json"), packet)
        raw = blank()
        audit = runner.assess_one(tmp_path, "controls", packet_id, FakeClient([json.dumps(raw)]))
        entries.append({"packet_id": packet_id, "expected": case["expected"]})
        passed = all(
            audit["assessment"]["questions"][q]["label"] in allowed
            for q, allowed in case["expected"].items()
        )
        results.append({"packet_id": packet_id, "passed": passed})
    write(tmp_path / "control-expectations.json", entries)
    write(tmp_path / "control-gate.json", {"passed": True, "results": results})
    with pytest.raises(ValueError, match="Stored control gate differs"):
        runner.verify_control_gate(tmp_path)
