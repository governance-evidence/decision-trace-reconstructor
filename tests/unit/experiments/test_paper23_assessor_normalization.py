"""Adversarial lexical recovery: no semantic edits or ambiguous object selection."""

import hashlib
import json

import pytest

from experiments.paper23_assessor_v2_normalization import extract


def test_exact_utf8_slice_and_labels_survive_preface():
    raw = '{"questions":{"Q7":{"label":"unsupported","evidence_ids":[]}}}'
    text = "Evidence summary: é.\n" + raw + "\nEnd."
    value, proof = extract(text)
    assert value == json.loads(raw)
    assert text.encode()[proof["utf8_start"] : proof["utf8_end"]].decode() == raw
    assert proof["slice_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert proof["exact_json_slice"] == raw


@pytest.mark.parametrize(
    "text",
    [
        '{"questions":{}} {"questions":{}}',
        '{"questions":{},"questions":{"Q7":{}}}',
        '{"questions":{"Q7":{"label":"unsupported"}}',
        '{"wrapper":{"questions":{}}',
        '{"other":1} {"questions":{}}',
        '{"questions":{"Q7":{"label":"unsupported","label":"fully_supported"}}}',
    ],
)
def test_reject_ambiguity_duplicate_keys_and_truncation(text):
    with pytest.raises(ValueError):
        extract(text)


@pytest.mark.parametrize("wrap", [lambda x: x, lambda x: "```json\n" + x + "\n```"])
def test_plain_and_fenced_json_with_quoted_braces(wrap):
    value = {"questions": {"Q7": {"answer": 'Quoted {braces} and "text" stay unchanged.'}}}
    assert extract(wrap(json.dumps(value)))[0] == value


def test_last_response_only_and_invalid_ids_stay_invalid(tmp_path):
    from pathlib import Path

    import experiments.paper23_assessor_v2_normalization as module
    from experiments.paper23.storage import read, write
    from experiments.paper23_assessor_v2.controls import controls
    from experiments.paper23_assessor_v2.rubric import OBLIGATIONS
    from experiments.paper23_assessor_v2.runner import sha
    from experiments.paper23_assessor_v2_normalization import recover_controls

    source = tmp_path / "source"
    target = tmp_path / "target"
    cases = controls()[:2]
    expectations = []
    for index, case in enumerate(cases):
        packet = case["packet"]
        pid = packet["packet_id"]
        base = {
            "questions": {
                q: {
                    "label": "unsupported",
                    "answer": "No adequate evidence",
                    "evidence": {slot: [] for slot in slots},
                    "missing": slots,
                    "contradictions": [],
                    "reason": "Missing",
                }
                for q, slots in OBLIGATIONS.items()
            }
        }
        first = json.loads(json.dumps(base))
        first["questions"]["Q7"]["label"] = "fully_supported"
        if index == 1:
            base["questions"]["Q7"]["evidence"]["final_state"] = ["not-in-packet"]
        write(
            source / "assessments/controls" / (pid + ".json"),
            {
                "status": "invalid_assessment",
                "responses": [
                    {"request_id": "first", "content": json.dumps(first)},
                    {"request_id": "last", "content": "Prefix\n" + json.dumps(base)},
                ],
            },
        )
        write(target / "packets/controls" / (pid + ".json"), packet)
        expectations.append({"packet_id": pid})
    write(source / "control-gate.json", {"passed": False})
    write(target / "control-expectations.json", expectations)
    write(
        target / "normalization-amendment.json",
        {
            "extension_sha256": sha(Path(module.__file__)),
            "predecessor": str(source),
            "predecessor_files": {
                str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file()
            },
        },
    )
    recover_controls(target)
    a = read(target / "assessments/controls" / (cases[0]["packet"]["packet_id"] + ".json"))
    assert a["assessment"]["questions"]["Q7"]["label"] == "unsupported"
    assert a["structural_recovery"]["last_response_request_id"] == "last"
    assert a["responses"][0]["content"] != a["responses"][1]["content"]
    b = read(target / "assessments/controls" / (cases[1]["packet"]["packet_id"] + ".json"))
    assert b["status"] == "invalid_assessment"
