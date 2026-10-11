"""Typed-eligibility regressions; no local rewriting of model judgements."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from experiments.paper23.storage import digest, read, write
from experiments.paper23_assessor_v3.controls import controls
from experiments.paper23_assessor_v3.rubric import OBLIGATIONS
from experiments.paper23_assessor_v4.rubric import status_snapshot
from experiments.paper23_assessor_v5 import lifecycle, runner
from experiments.paper23_assessor_v5.rubric import (
    admissibility,
    derive,
    eligibility,
    model_view,
    schema,
    validate,
)


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


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, run_id, messages):
        self.calls.append(deepcopy(messages))
        return {
            "choices": [{"message": {"content": next(self.responses)}, "finish_reason": "stop"}]
        }, str(len(self.calls))


def packet(name):
    return next(c["packet"] for c in controls() if c["name"] == name)


def retained(packet_id):
    root = Path(__file__).resolve().parents[3] / "study-data/paper23-20261010-assessor-v4"
    if not root.exists():
        pytest.skip("Local V4 evidence not distributed in source checkout")
    return (
        read(root / "packets/controls" / (packet_id + ".json")),
        read(root / "assessments/controls" / (packet_id + ".json"))["raw_assessment"],
    )


@pytest.mark.parametrize("packet_id", ["738cf3d0cf771422", "d99a02126aa48119"])
def test_retained_v4_failures_rejected_without_rewriting(packet_id):
    p, raw = retained(packet_id)
    before = digest(raw)
    with pytest.raises(ValueError, match="out-of-role"):
        validate(raw, p)
    assert digest(raw) == before


def test_config_exception_can_remove_extra_authority_without_relabelling():
    p, raw = retained("738cf3d0cf771422")
    locked = status_snapshot(raw)
    raw["questions"]["Q2"]["evidence"]["human_decisions"] = eligibility(p)["Q2.human_decisions"][
        "not_required"
    ]
    validate(raw, p, locked)
    assert admissibility(derive(raw), p) == []
    assert status_snapshot(raw) == locked


def test_receipt_partial_cannot_be_repaired_by_changing_status():
    p, raw = retained("d99a02126aa48119")
    locked = status_snapshot(raw)
    raw["questions"]["Q7"]["evidence"]["final_state"] = []
    raw["questions"]["Q7"]["statuses"]["final_state"] = "missing"
    with pytest.raises(ValueError, match="locked obligation"):
        validate(raw, p, locked)
    slot = schema(p)["properties"]["questions"]["properties"]["Q7"]["properties"]
    assert slot["statuses"]["properties"]["final_state"]["enum"] == ["missing"]
    assert slot["evidence"]["properties"]["final_state"]["maxItems"] == 0


@pytest.mark.parametrize(
    "name",
    [
        "complete_commit",
        "documented_refusal",
        "documented_human_two_attempts",
        "unresolved_state_conflict",
    ],
)
def test_positive_and_conflict_controls_keep_genuine_records_eligible(name):
    p = packet(name)
    index = eligibility(p)
    assert index["Q7.execution_receipts"]
    assert index["Q7.final_state"]
    if name == "documented_human_two_attempts":
        assert len(index["Q2.human_decisions"]["decisions"]) == 2
        assert not index["Q2.human_decisions"]["not_required"]
    if name == "unresolved_state_conflict":
        assert len(index["Q7.final_state"]) == 2


@pytest.mark.parametrize("mutation", ["wrong_kind", "wrong_actor", "no_state", "early"])
def test_fake_or_early_independent_observation_is_ineligible(mutation):
    p = packet("complete_commit")
    final = next(r for r in p["records"] if r["kind"] == "final_state_check")
    if mutation == "wrong_kind":
        final["kind"] = "model_output"
    elif mutation == "wrong_actor":
        final["actor"] = "agent"
    elif mutation == "no_state":
        del final["data"]["actual_state"]
    else:
        final["time"] = 6.5
    assert not eligibility(p)["Q7.final_state"]


@pytest.mark.parametrize("mutation", ["unmatched", "early", "pre_action"])
def test_unmatched_or_early_receipt_is_ineligible(mutation):
    p = packet("complete_commit")
    receipt = next(r for r in p["records"] if r["data"].get("status") == "committed")
    if mutation == "unmatched":
        receipt["data"]["call_id"] = "other-call"
    elif mutation == "early":
        receipt["time"] = 5.5
    else:
        receipt["data"]["phase"] = "before"
    assert not eligibility(p)["Q7.execution_receipts"]


def test_eligibility_is_not_a_positive_label_and_view_has_no_targets():
    p = packet("complete_commit")
    assert eligibility(p)["Q7.final_state"]
    validate(blank(), p)
    view = model_view(p)
    assert set(view) == {"packet_id", "records", "eligibility_index"}
    assert view["records"] == p["records"]
    assert "fully_supported" not in json.dumps(view)


def test_duplicate_ids_refused():
    p = packet("complete_commit")
    p["records"].append(deepcopy(p["records"][0]))
    with pytest.raises(ValueError, match="unique"):
        eligibility(p)


def test_schemas_have_no_empty_enums():
    def walk(node):
        if isinstance(node, dict):
            if "enum" in node:
                assert node["enum"]
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for case in controls():
        walk(schema(case["packet"]))


def test_correction_retains_two_raw_responses_and_locked_statuses(tmp_path):
    p, raw = retained("738cf3d0cf771422")
    fixed = deepcopy(raw)
    fixed["questions"]["Q2"]["evidence"]["human_decisions"] = eligibility(p)["Q2.human_decisions"][
        "not_required"
    ]
    write(tmp_path / "packets/controls" / (p["packet_id"] + ".json"), p)
    audit = runner.assess_one(
        tmp_path, "controls", p["packet_id"], FakeClient([json.dumps(raw), json.dumps(fixed)])
    )
    assert audit["status"] == "complete"
    assert len(audit["responses"]) == 2
    assert audit["locked_statuses"] == status_snapshot(raw)
    assert runner.replay_assessment(audit, p) == audit


def test_failed_gate_blocks_main_without_call(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify_freeze", lambda root: None)
    monkeypatch.setattr(runner, "verify_control_gate", lambda root: {"passed": False})
    client = FakeClient([])
    with pytest.raises(ValueError, match="Control gate failed"):
        runner.run_main(tmp_path, client)
    assert not client.calls


def test_named_predecessor_freeze_ignores_new_sibling_but_detects_edit(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    root = tmp_path / "study"
    write(repo / "old.json", {"original": True})
    write(root / "packet.json", {"original": True})
    write(
        root / "freeze.json",
        {
            "code": {"old.json": lifecycle.sha(repo / "old.json")},
            "inputs": {"packet.json": lifecycle.sha(root / "packet.json")},
        },
    )
    monkeypatch.setattr(lifecycle, "REPO", repo)
    write(repo / "new.json", {"new": True})
    lifecycle.verify_named_freeze(root)
    write(repo / "old.json", {"original": False})
    with pytest.raises(ValueError, match="predecessor code"):
        lifecycle.verify_named_freeze(root)
