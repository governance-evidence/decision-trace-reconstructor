"""Explicit incomplete-reference continuation; never repairs failed AI labels.

The frozen judge, rubric, adapter, instrument and metric functions are imported
unchanged. This extension is separately hashed before any main DTR disclosure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from experiments.paper23.client import Client, load_key
from experiments.paper23.packets import ROWS, adapt, baseline, crosswalk
from experiments.paper23.runner import source_hash
from experiments.paper23.storage import digest, read, write
from experiments.paper23_analysis.judge import assess, validate
from experiments.paper23_analysis.scoring import (
    analysis_hashes,
    metrics,
    paired,
    pin_instrument,
)


def own_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def verify_original(study):
    config = read(study / "study.json")
    protocol = read(study / "protocol-freeze.json")
    analysis = read(study / "analysis-freeze.json")
    assert digest(config) == protocol["study_sha256"]
    assert source_hash() == config["source_hash"]
    assert analysis_hashes() == analysis["files"]
    assert digest(analysis) == config["analysis_freeze_sha256"]
    reduced = read(study / "annotations/main-reduced.frozen.json")
    assert digest(read(study / "annotations/main-reduced.json")) == reduced["source_sha256"]
    assert digest(reduced["annotations"]) == reduced["source_sha256"]


def continue_assessment(study, client):
    verify_original(study)
    path = study / "annotations/main-full.json"
    form = read(path)
    ledger = study / "recovery/amendment.json"
    if not ledger.exists():
        assert not (study / "scores/main").exists()
        failed = [
            p.stem
            for p in (study / "judge-attempts/main").glob("*.json")
            if read(p)["status"] == "invalid_assessment"
        ]
        assert failed
        write(study / "recovery/original-full-form.json", form)
        write(
            ledger,
            {
                "time": time.time(),
                "extension_sha256": own_hash(),
                "reason": "AI assessment invalid after the prespecified one correction; no further attempt or manual label repair",
                "initial_failed_packets": sorted(failed),
                "original_code_unchanged": True,
                "main_dtr_predictions_generated": False,
                "continuation": "Unchanged judge.assess on one-packet workspaces for unattempted packets only, same client and aggregate budget",
                "reference_policy": "Preserve complete valid answers; every failed packet has null reference for all six rows and is excluded from reference-relative and paired comparisons",
                "analysis_status": "Original all-valid primary freeze cannot be met; separately reported incomplete-reference supplemental analysis",
            },
        )
    assert read(ledger)["extension_sha256"] == own_hash()
    for item in form["packets"]:
        packet_id = item["packet_id"]
        audit_path = study / "judge-attempts/main" / (packet_id + ".json")
        if not audit_path.exists():
            work = study / "recovery/assessment-workspaces" / packet_id
            if work.exists():
                raise ValueError("Reconcile an interrupted continuation workspace before retrying")
            write(
                work / "annotations/main-full.json",
                {
                    "origin": "ai_assessed",
                    "independent_human_validation": False,
                    "pass": "full",
                    "packets": [item],
                },
            )
            reduced_path = work / "annotations/main-reduced.frozen.json"
            shutil.copyfile(study / "annotations/main-reduced.frozen.json", reduced_path)
            packet_target = work / "packets/main" / (packet_id + ".json")
            packet_target.parent.mkdir(parents=True)
            shutil.copyfile(study / "packets/main" / (packet_id + ".json"), packet_target)
            try:
                assess(work, "main", "full", client)
            except ValueError:
                audit = read(work / "judge-attempts/main" / (packet_id + ".json"))
                if audit["status"] != "invalid_assessment":
                    raise
            audit = read(work / "judge-attempts/main" / (packet_id + ".json"))
            write(audit_path, audit)
        audit = read(audit_path)
        packet = read(study / "packets/main" / (packet_id + ".json"))
        assert audit["packet_sha256"] == digest(packet)
        if audit["status"] == "complete":
            validate({"questions": audit["assessment"]["questions"]}, packet)
            item.update(audit["assessment"])
            item["assessment_status"] = "complete"
        elif audit["status"] == "invalid_assessment":
            assert len(audit["responses"]) == 2
            assert not item.get("annotator")
            assert all(q["label"] is None for q in item["questions"].values())
            item["assessment_status"] = "invalid_assessment"
            item["failure_record"] = str(audit_path.relative_to(study))
        else:
            raise ValueError("Unresolved API attempt must not be treated as an invalid judgement")
        write(path, form)
        print(json.dumps({"packet": packet_id, "assessment_status": audit["status"]}), flush=True)
    assert len(form["packets"]) == 36
    statuses = Counter(x["assessment_status"] for x in form["packets"])
    assert statuses["invalid_assessment"] > 0
    frozen_path = study / "annotations/main-full.incomplete-frozen.json"
    if frozen_path.exists():
        raise ValueError("Incomplete reference has already been frozen")
    write(
        frozen_path,
        {
            "frozen": time.time(),
            "source_sha256": digest(form),
            "annotations": form,
            "coverage": dict(statuses),
            "extension_sha256": own_hash(),
            "primary_complete_coverage_gate": "not_met",
            "independent_human_validation": False,
        },
    )
    return {"full_reference_coverage": dict(statuses), "budget": client.budget.summary()}


def score_incomplete(study):
    verify_original(study)
    frozen = read(study / "annotations/main-full.incomplete-frozen.json")
    assert (
        frozen["extension_sha256"]
        == own_hash()
        == read(study / "recovery/amendment.json")["extension_sha256"]
    )
    assert digest(read(study / "annotations/main-full.json")) == frozen["source_sha256"]
    assert digest(frozen["annotations"]) == frozen["source_sha256"]
    reduced = read(study / "annotations/main-reduced.frozen.json")["annotations"]["packets"]
    answers = {x["packet_id"]: x for x in reduced}
    failed = []
    for x in frozen["annotations"]["packets"]:
        if x["assessment_status"] == "complete":
            answers[x["packet_id"]] = x
        else:
            failed.append(x["packet_id"])
    index = read(study / "main-packet-index.json")
    assert set(answers) | set(failed) == {x["packet_id"] for x in index}
    instrument = pin_instrument(study)
    output = study / "scores/main-reference-incomplete"
    output.mkdir(parents=True, exist_ok=False)
    began = time.time()
    rows, failures, opaque = [], [], []
    for entry in index:
        packet_id = entry["packet_id"]
        packet = read(study / "packets/main" / (packet_id + ".json"))
        assert digest(packet) == entry["sha256"]
        manifest = output / packet_id / "manifest.json"
        write(manifest, adapt(packet))
        started = time.time()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "reconstructor.cli",
                "reconstruct",
                str(manifest),
                "--out",
                str(manifest.parent),
            ],
            cwd=instrument,
            capture_output=True,
            text=True,
            timeout=45,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(instrument / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        write(
            manifest.parent / "process.json",
            {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "started": started,
                "ended": time.time(),
            },
        )
        if result.returncode:
            predictions = {}
            failures.append(packet_id)
        else:
            report = read(manifest.parent / "feasibility.json")
            predictions = {x["property"]: x["category"] for x in report["per_property"]}
            opaque.append(
                {
                    "packet_id": packet_id,
                    "verdict": next(
                        x for x in report["per_property"] if x["property"] == "reasoning_trace"
                    ),
                }
            )
        reference = crosswalk(answers[packet_id]["questions"]) if packet_id in answers else {}
        simple = baseline(packet)
        for prop, questions in ROWS.items():
            exclusions = (
                [answers[packet_id]["questions"][q].get("exclusion") for q in questions]
                if packet_id in answers
                else ["AI assessment failed packet-local evidence-ID validation"]
            )
            rows.append(
                {
                    "packet_id": packet_id,
                    "run_id": entry["run_id"],
                    "condition": entry["condition"],
                    "architecture": packet["architecture"],
                    "tier": packet["tier"],
                    "property": prop,
                    "reference": reference.get(prop),
                    "dtr": predictions.get(prop, "processing_failure"),
                    "baseline": simple[prop],
                    "excluded": any(exclusions),
                    "exclusion_reasons": exclusions,
                    "reference_available": packet_id in answers,
                }
            )
    summary = {
        "analysis_status": "Supplemental incomplete-reference analysis; original all-valid primary gate not met",
        "reference_type": "AI assessed, not independent human ground truth",
        "instrument_commit": read(study / "study.json")["instrument_commit"],
        "extension_sha256": own_hash(),
        "packets_scored": len(index) - len(failures),
        "packet_failures": failures,
        "packets_with_valid_reference": len(answers),
        "reference_failures": failed,
        "observable_rows": len(rows),
        "dtr": metrics(rows),
        "baseline": metrics(rows, "baseline"),
        "paired_dtr": paired(rows),
        "paired_baseline": paired(rows, "baseline"),
        "breakdowns": {
            d: {v: metrics([r for r in rows if r[d] == v]) for v in sorted({r[d] for r in rows})}
            for d in ("property", "condition", "architecture", "tier")
        },
        "opaque_reasoning": opaque,
        "elapsed_scoring_s": time.time() - began,
        "cautions": [
            "Missing AI references are excluded, never recoded unsupported",
            "Conditional agreement is vulnerable to non-random missingness",
            "Paired views/property rows are dependent; no population intervals",
            "Same model generates and assesses; no independent human validation",
            "Infrastructure actors and unresolved parent IDs confound causal/architecture interpretation",
        ],
    }
    write(output / "rows.json", rows)
    write(output / "summary.json", summary)
    write(
        output / "discrepancies.json",
        [
            r
            for r in rows
            if not r["excluded"]
            and ((r["dtr"] == "fully_fillable") != (r["reference"] == "fully_supported"))
        ],
    )
    return {
        "packets_scored": summary["packets_scored"],
        "valid_reference_packets": len(answers),
        "reference_failures": failed,
        "processing_failures": failures,
        "summary": str(output / "summary.json"),
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["continue", "score"])
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    study = args.study.resolve()
    result = (
        continue_assessment(study, Client(study, load_key(args.env_file)))
        if args.command == "continue"
        else score_incomplete(study)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
