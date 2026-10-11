"""Freeze, assess and preserve v2 without writes to its historical source."""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import time
from pathlib import Path

from experiments.paper23.storage import digest, read, write

from .client import MODEL, PROVIDER
from .controls import controls
from .rubric import PROMPT, admissibility, model_view, project, validate

MODULE = Path(__file__).parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def own_hashes():
    return {p.name: sha(p) for p in sorted(MODULE.glob("*.py"))}


def verify_original(root):
    record = read(root / "original-preservation-before.json")
    old = Path(record["root"])
    current = {str(p.relative_to(old)): sha(p) for p in sorted(old.rglob("*")) if p.is_file()}
    if (
        current != record["files"]
        or sha(old.parent / "paper23-20261010-delivery.zip") != record["delivery_zip_sha256"]
    ):
        raise ValueError("Original study or delivery changed")
    return {"original_files_unchanged": len(current), "original_zip_unchanged": True}


def prepare(root, original, protocol):
    root, original = Path(root), Path(original)
    if (root / "run.json").exists():
        raise ValueError("A prepared run must not be replaced")
    verify_original(root)
    preflight = read(root / "provider-preflight.json")["model"]
    if (
        preflight["id"] != MODEL
        or float(preflight["pricing"]["prompt"]) > 3 / 1e6
        or float(preflight["pricing"]["completion"]) > 15 / 1e6
        or "structured_outputs" not in preflight["supported_parameters"]
    ):
        raise ValueError("Current model metadata does not meet protocol")
    shutil.copyfile(protocol, root / "protocol.md")
    write(root / "budget.json", read(original / "budget.json"))
    index = read(original / "main-packet-index.json")
    projected = []
    for entry in index:
        path = original / "packets/main" / (entry["packet_id"] + ".json")
        packet = read(path)
        if digest(packet) != entry["sha256"]:
            raise ValueError("Original packet no longer matches original index")
        view, removed = project(packet)
        dest = root / "packets/main" / path.name
        write(dest, view)
        projected.append(
            {
                **entry,
                "original_sha256_bytes": sha(path),
                "projected_sha256_bytes": sha(dest),
                "sha256": digest(view),
                "removed_fields": removed,
            }
        )
    write(root / "main-packet-index.json", projected)
    for pass_name in ("reduced", "full"):
        order = [
            r["packet_id"]
            for r in read(original / "annotations" / f"main-{pass_name}.json")["packets"]
        ]
        write(root / f"{pass_name}-order.json", order)
    cases = controls()
    random.Random(231020).shuffle(cases)
    expected = []
    for case in cases:
        packet = case["packet"]
        write(root / "packets/controls" / (packet["packet_id"] + ".json"), packet)
        expected.append(
            {k: v for k, v in case.items() if k != "packet"} | {"packet_id": packet["packet_id"]}
        )
    write(root / "control-expectations.json", expected)
    write(
        root / "run.json",
        {
            "created": time.time(),
            "original": str(original.resolve()),
            "model": MODEL,
            "provider": PROVIDER,
            "old_budget_requests": len(read(original / "budget.json")["requests"]),
            "old_budget_sha256": sha(original / "budget.json"),
            "original_source_hashes": {
                str(p.relative_to(MODULE.parent.parent)): sha(p)
                for folder in ("paper23", "paper23_analysis")
                for p in sorted((MODULE.parent / folder).glob("*.py"))
            }
            | {
                str((MODULE.parent / "paper23_recovery.py").relative_to(MODULE.parent.parent)): sha(
                    MODULE.parent / "paper23_recovery.py"
                )
            },
            "independent_human_validation": False,
            "original_result_known": True,
            "analysis_design": "exploratory_joint_model_protocol_projection_change",
        },
    )
    return {"prepared": True, "main_packets": len(projected), "controls": len(cases)}


def freeze(root):
    target = root / "freeze.json"
    if target.exists() or (root / "transport").exists():
        raise ValueError("Freeze already exists or paid calls occurred")
    files = [
        root / "protocol.md",
        root / "run.json",
        root / "provider-preflight.json",
        root / "main-packet-index.json",
        root / "control-expectations.json",
        root / "reduced-order.json",
        root / "full-order.json",
        *sorted((root / "packets").rglob("*.json")),
    ]
    write(
        target,
        {
            "time": time.time(),
            "code": own_hashes(),
            "inputs": {str(p.relative_to(root)): sha(p) for p in files},
        },
    )
    return {"frozen": True, "files": len(files), "code_modules": len(own_hashes())}


def verify_freeze(root):
    frozen = read(root / "freeze.json")
    if frozen["code"] != own_hashes() or any(
        sha(root / p) != h for p, h in frozen["inputs"].items()
    ):
        raise ValueError("Frozen code or inputs changed")
    config = read(root / "run.json")
    if any(sha(MODULE.parent.parent / p) != h for p, h in config["original_source_hashes"].items()):
        raise ValueError("Original study module changed")


def assess_one(root, phase, packet_id, client):
    target = root / "assessments" / phase / (packet_id + ".json")
    if target.exists():
        record = read(target)
        if record["status"] in ("complete", "invalid_assessment"):
            return record
        raise ValueError("Unresolved assessment attempt; do not silently repeat")
    packet = read(root / "packets" / phase / (packet_id + ".json"))
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": json.dumps(model_view(packet), ensure_ascii=False)},
    ]
    audit = {
        "packet_id": packet_id,
        "packet_sha256": digest(packet),
        "started": time.time(),
        "status": "calling_model",
        "responses": [],
    }
    write(target, audit)
    for attempt in range(2):
        response, request_id = client.complete(f"assessor-v2-{phase}-{packet_id}", messages)
        text = response["choices"][0]["message"].get("content") or ""
        audit["responses"].append(
            {
                "request_id": request_id,
                "content": text,
                "finish_reason": response["choices"][0].get("finish_reason"),
            }
        )
        write(target, audit)
        try:
            value = validate(json.loads(text), packet)
        except (ValueError, TypeError, KeyError) as exc:
            audit["responses"][-1]["validation_error"] = str(exc)
            if attempt == 1:
                audit.update(status="invalid_assessment", ended=time.time())
                write(target, audit)
                return audit
            write(target, audit)
            messages += [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": "Correct ONLY this JSON schema or packet-ID error, without changing evidence or receiving semantic feedback: "
                    + str(exc),
                },
            ]
            continue
        audit.update(
            status="complete",
            assessment=value,
            admissibility_flags=admissibility(value, packet),
            ended=time.time(),
        )
        write(target, audit)
        return audit
    raise AssertionError("Unreachable")


def run_controls(root, client):
    verify_freeze(root)
    if (root / "control-gate.json").exists():
        return read(root / "control-gate.json")
    results = []
    for case in read(root / "control-expectations.json"):
        audit = assess_one(root, "controls", case["packet_id"], client)
        passed = audit["status"] == "complete" and not audit.get("admissibility_flags")
        if audit["status"] == "complete":
            passed = passed and all(
                audit["assessment"]["questions"][q]["label"] in allowed
                for q, allowed in case["expected"].items()
            )
        results.append(
            {
                "name": case["name"],
                "packet_id": case["packet_id"],
                "passed": passed,
                "status": audit["status"],
                "expected": case["expected"],
                "observed": {
                    q: audit.get("assessment", {}).get("questions", {}).get(q, {}).get("label")
                    for q in case["expected"]
                },
                "admissibility_flags": audit.get("admissibility_flags", []),
            }
        )
        print(json.dumps(results[-1]), flush=True)
    gate = {
        "passed": all(r["passed"] for r in results),
        "results": results,
        "time": time.time(),
        "rule": "all prespecified controls pass; semantic failure blocks main",
        "human_validation": False,
    }
    write(root / "control-gate.json", gate)
    return gate


def run_main(root, client):
    verify_freeze(root)
    if read(root / "control-gate.json")["passed"] is not True:
        raise ValueError("Control gate failed; main inference prohibited")
    for pass_name in ("reduced", "full"):
        target = root / "annotations" / f"{pass_name}.frozen.json"
        if target.exists():
            frozen = read(target)
            if digest(frozen["assessments"]) != frozen["source_sha256"]:
                raise ValueError("Frozen annotations changed")
            continue
        rows = []
        for packet_id in read(root / f"{pass_name}-order.json"):
            audit = assess_one(root, "main", packet_id, client)
            rows.append(audit)
            print(
                json.dumps(
                    {
                        "pass": pass_name,
                        "packet_id": packet_id,
                        "status": audit["status"],
                        "flags": len(audit.get("admissibility_flags", [])),
                        "done": len(rows),
                    }
                ),
                flush=True,
            )
        write(
            target,
            {
                "time": time.time(),
                "model": MODEL,
                "origin": "ai_assessed",
                "independent_human_validation": False,
                "assessments": rows,
                "source_sha256": digest(rows),
            },
        )
    return {"main_assessments": 72, "budget": client.budget.summary()}
