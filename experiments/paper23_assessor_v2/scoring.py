"""Unchanged DTR/metric functions on the assessor's projected record population."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from experiments.paper23.packets import ROWS, adapt, baseline, crosswalk
from experiments.paper23.storage import digest, read, write
from experiments.paper23_analysis.scoring import metrics, paired, pin_instrument

from .runner import verify_freeze


def score(root, output=None):
    root = Path(root)
    verify_freeze(root)
    if read(root / "control-gate.json")["passed"] is not True:
        raise ValueError("Failed controls do not permit main scoring")
    answers = {}
    for pass_name in ("reduced", "full"):
        frozen = read(root / "annotations" / f"{pass_name}.frozen.json")
        if digest(frozen["assessments"]) != frozen["source_sha256"]:
            raise ValueError("Frozen annotations changed")
        for item in frozen["assessments"]:
            if item["packet_id"] in answers:
                raise ValueError("Duplicate packet assessment")
            answers[item["packet_id"]] = item
    index = read(root / "main-packet-index.json")
    if set(answers) != {e["packet_id"] for e in index}:
        raise ValueError("Assessment coverage differs from frozen packet population")
    instrument = pin_instrument(root)
    output = Path(output) if output else root / "scores"
    if output.exists():
        raise ValueError("Do not overwrite retained results")
    output.mkdir(parents=True)
    rows = []
    flags = []
    failures = []
    started = time.time()
    for entry in index:
        packet_id = entry["packet_id"]
        packet = read(root / "packets/main" / (packet_id + ".json"))
        if digest(packet) != entry["sha256"]:
            raise ValueError("Packet changed")
        manifest = output / packet_id / "manifest.json"
        write(manifest, adapt(packet))
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "reconstructor.cli",
                "reconstruct",
                str(manifest.resolve()),
                "--out",
                str(manifest.parent.resolve()),
            ],
            cwd=instrument,
            capture_output=True,
            text=True,
            timeout=45,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str((instrument / "src").resolve()),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        write(
            manifest.parent / "process.json",
            {"returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr},
        )
        predictions = {}
        if process.returncode:
            failures.append(packet_id)
        else:
            predictions = {
                x["property"]: x["category"]
                for x in read(manifest.parent / "feasibility.json")["per_property"]
            }
        audit = answers[packet_id]
        available = audit["status"] == "complete"
        reference = crosswalk(audit["assessment"]["questions"]) if available else {}
        simple = baseline(packet)
        flags += [{"packet_id": packet_id, **f} for f in audit.get("admissibility_flags", [])]
        for prop in ROWS:
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
                    "excluded": not available,
                    "exclusion_reasons": []
                    if available
                    else ["invalid_assessment_after_one_structural_correction"],
                }
            )
    summary = {
        "reference_type": "Alternative-model AI assessment; no independent human ground truth",
        "packets_scored": len(index) - len(failures),
        "packet_failures": failures,
        "schema_valid_packets": sum(a["status"] == "complete" for a in answers.values()),
        "schema_failed_packets": [k for k, a in answers.items() if a["status"] != "complete"],
        "admissibility_flags": flags,
        "reference_contract_gate_passed": not flags,
        "dtr": metrics(rows),
        "baseline": metrics(rows, "baseline"),
        "paired_dtr": paired(rows),
        "paired_baseline": paired(rows, "baseline"),
        "question_labels": dict(
            Counter(
                i["label"]
                for a in answers.values()
                if a["status"] == "complete"
                for i in a["assessment"]["questions"].values()
            )
        ),
        "elapsed_scoring_s": time.time() - started,
        "cautions": [
            "Engineered control success is not independent validation",
            "Same trajectories; exploratory joint model, prompt and projection change",
            "Admissibility flags do not relabel or selectively exclude schema-valid answers",
            "Dependent views and properties; no population accuracy or architecture ranking",
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
        "schema_valid_packets": summary["schema_valid_packets"],
        "admissibility_flags": len(flags),
        "elapsed_scoring_s": summary["elapsed_scoring_s"],
    }


def compare(root):
    old = Path(read(root / "run.json")["original"])
    prior = {p.stem: read(p) for p in (old / "judge-attempts/main").glob("*.json")}
    current = {p.stem: read(p) for p in (root / "assessments/main").glob("*.json")}
    transitions = []
    newly_covered = []
    for packet_id, a in current.items():
        b = prior[packet_id]
        if a["status"] != "complete":
            continue
        if b["status"] != "complete":
            newly_covered.append(packet_id)
            continue
        for q in a["assessment"]["questions"]:
            transitions.append(
                {
                    "packet_id": packet_id,
                    "question": q,
                    "v1": b["assessment"]["questions"][q]["label"],
                    "v2": a["assessment"]["questions"][q]["label"],
                }
            )
    old_rows = {
        (r["packet_id"], r["property"]): r
        for r in read(old / "scores/main-reference-incomplete/rows.json")
    }
    changes = []
    for row in read(root / "scores/rows.json"):
        before = old_rows[(row["packet_id"], row["property"])]
        for field in ("dtr", "baseline"):
            if before[field] != row[field]:
                changes.append(
                    {
                        "packet_id": row["packet_id"],
                        "property": row["property"],
                        "field": field,
                        "v1": before[field],
                        "v2": row[field],
                    }
                )
    controls = {}
    for condition, q in [("A", "Q2"), ("O", "Q7"), ("full", "Q7")]:
        ids = [
            e["packet_id"]
            for e in read(root / "main-packet-index.json")
            if e["condition"] == condition
        ]
        controls[condition + "_" + q] = {
            "population": len(ids),
            "labels": dict(
                Counter(
                    current[i]
                    .get("assessment", {})
                    .get("questions", {})
                    .get(q, {})
                    .get("label", "missing")
                    for i in ids
                )
            ),
        }
    result = {
        "common_question_labels": len(transitions),
        "transitions": [
            {"v1": a, "v2": b, "count": n}
            for (a, b), n in sorted(Counter((x["v1"], x["v2"]) for x in transitions).items())
        ],
        "newly_covered_historical_failures": newly_covered,
        "projection_prediction_changes": changes,
        "main_deletion_checks": controls,
        "interpretation": "exploratory joint model/protocol/projection change; no isolated causal model effect",
    }
    write(root / "comparison.json", result)
    write(root / "question-transitions.json", transitions)
    return result
