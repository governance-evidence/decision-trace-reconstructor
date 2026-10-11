"""Regression for preserving failed references during bounded continuation."""

from types import SimpleNamespace

from experiments import paper23_recovery as recovery
from experiments.paper23.packets import QUESTIONS
from experiments.paper23.storage import digest, read, write


def test_continuation_keeps_failure_and_does_not_requery_attempted_packets(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "verify_original", lambda study: None)
    questions = {
        q: {"label": None, "answer": None, "reason": None, "evidence_ids": [], "exclusion": None}
        for q in QUESTIONS
    }
    form = {
        "origin": "ai_assessed",
        "independent_human_validation": False,
        "pass": "full",
        "packets": [],
    }
    for i in range(36):
        packet_id = f"packet-{i:02d}"
        form["packets"].append({"packet_id": packet_id, "annotator": None, "questions": questions})
        write(
            tmp_path / "packets/main" / f"{packet_id}.json",
            {"packet_id": packet_id, "records": [{"id": "record-1"}]},
        )
    write(tmp_path / "annotations/main-full.json", form)
    reduced = {"source_sha256": "genuine-fixture-freeze", "annotations": {"origin": "ai_assessed"}}
    write(tmp_path / "annotations/main-reduced.frozen.json", reduced)

    def completed(packet_id):
        packet = read(tmp_path / "packets/main" / f"{packet_id}.json")
        return {
            "status": "complete",
            "packet_id": packet_id,
            "packet_sha256": digest(packet),
            "responses": [{"request_id": packet_id}],
            "assessment": {
                "annotator": "AI fixture",
                "questions": {
                    q: {
                        "label": "unsupported",
                        "answer": "Unknown",
                        "reason": "No adequate record",
                        "evidence_ids": [],
                        "exclusion": None,
                    }
                    for q in QUESTIONS
                },
            },
        }

    write(tmp_path / "judge-attempts/main/packet-00.json", completed("packet-00"))
    failed_path = tmp_path / "judge-attempts/main/packet-01.json"
    write(
        failed_path,
        {
            "status": "invalid_assessment",
            "packet_id": "packet-01",
            "packet_sha256": digest(read(tmp_path / "packets/main/packet-01.json")),
            "responses": [{"validation_error": "invalid ID"}, {"validation_error": "invalid ID"}],
        },
    )
    failed_bytes = failed_path.read_bytes()
    calls = []
    client = SimpleNamespace(budget=SimpleNamespace(summary=lambda: {"cap_usd": 5}))

    def mock_assess(work, phase, pass_name, supplied_client):
        assert supplied_client is client
        assert read(work / "annotations/main-reduced.frozen.json") == reduced
        item = read(work / "annotations/main-full.json")["packets"][0]
        pid = item["packet_id"]
        assert (work / "packets/main" / f"{pid}.json").read_bytes() == (
            tmp_path / "packets/main" / f"{pid}.json"
        ).read_bytes()
        calls.append(pid)
        write(work / "judge-attempts/main" / f"{pid}.json", completed(pid))

    monkeypatch.setattr(recovery, "assess", mock_assess)
    result = recovery.continue_assessment(tmp_path, client)
    assert calls == [f"packet-{i:02d}" for i in range(2, 36)]
    assert failed_path.read_bytes() == failed_bytes
    assert result["full_reference_coverage"] == {"complete": 35, "invalid_assessment": 1}
    frozen = read(tmp_path / "annotations/main-full.incomplete-frozen.json")
    failure = frozen["annotations"]["packets"][1]
    assert failure["annotator"] is None
    assert all(q["label"] is None for q in failure["questions"].values())
    assert not (tmp_path / "annotations/main-full.frozen.json").exists()
    assert frozen["primary_complete_coverage_gate"] == "not_met"
