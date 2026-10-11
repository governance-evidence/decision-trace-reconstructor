"""Durable calls and the unchanged all-controls-before-main sequence."""

import json
import time

from experiments.paper23.storage import digest, read, write
from experiments.paper23_assessor_v2_normalization import extract

from .client import MODEL
from .lifecycle import verify_freeze
from .rubric import PROMPT, admissibility, derive, model_view, status_snapshot, validate


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
    locked_statuses = {}
    for attempt in range(2):
        response, request_id = client.complete(f"assessor-v5-{phase}-{packet_id}", messages)
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
            value, normalization = extract(text)
            audit["responses"][-1]["normalization"] = normalization
            if attempt == 0:
                locked_statuses = status_snapshot(value)
                audit["locked_statuses"] = locked_statuses
            if response["choices"][0].get("finish_reason") != "stop":
                raise ValueError("Response did not finish normally; return complete JSON")
            value = validate(value, packet, locked_statuses)
            derived = derive(value)
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
                    "content": "Return the ENTIRE corrected JSON object Q1-Q7 and no prose. Correct ONLY the output-encoding constraint below. Preserve every obligation status; do not change judgements. No target labels or semantic feedback are supplied. Constraint: "
                    + str(exc),
                },
            ]
            continue
        audit.update(
            status="complete",
            assessment=derived,
            raw_assessment=value,
            normalization=normalization,
            admissibility_flags=admissibility(derived, packet),
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
    if verify_control_gate(root)["passed"] is not True:
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


def verify_control_gate(root):
    """Recompute acceptance from raw retained responses, not a trusted boolean."""
    verify_freeze(root)
    gate = read(root / "control-gate.json")
    results = []
    cases = read(root / "control-expectations.json")
    if len(cases) != 10:
        raise ValueError("Exactly ten frozen controls are required")
    for case in cases:
        audit = read(root / "assessments/controls" / (case["packet_id"] + ".json"))
        packet = read(root / "packets/controls" / (case["packet_id"] + ".json"))
        result = replay_assessment(audit, packet)
        passed = result["status"] == "complete" and not result.get("admissibility_flags")
        if passed:
            passed = all(
                result["assessment"]["questions"][q]["label"] in allowed
                for q, allowed in case["expected"].items()
            )
        saved = next(r for r in gate["results"] if r["packet_id"] == case["packet_id"])
        if saved["passed"] != passed:
            raise ValueError("Stored control outcome differs from offline replay")
        results.append(passed)
    if gate["passed"] != all(results):
        raise ValueError("Stored control gate differs from offline replay")
    return gate


def replay_assessment(audit, packet):
    if audit["packet_sha256"] != digest(packet) or not 1 <= len(audit["responses"]) <= 2:
        raise ValueError("Assessment input or response count mismatch")
    locked = {}
    accepted = None
    for attempt, response in enumerate(audit["responses"]):
        try:
            raw, proof = extract(response["content"])
            if attempt == 0:
                locked = status_snapshot(raw)
            if response["finish_reason"] != "stop":
                raise ValueError("Non-stop response")
            validate(raw, packet, locked)
        except (ValueError, TypeError, KeyError):
            if accepted is not None:
                raise ValueError("Unexpected extra response after acceptance") from None
            continue
        if accepted is not None or attempt != len(audit["responses"]) - 1:
            raise ValueError("Unexpected correction of an already accepted response")
        accepted = (raw, proof)
    if accepted is None:
        if audit["status"] != "invalid_assessment":
            raise ValueError("Saved acceptance differs from raw response replay")
        return audit
    raw, proof = accepted
    derived = derive(raw)
    flags = admissibility(derived, packet)
    if (
        audit["status"] != "complete"
        or audit["raw_assessment"] != raw
        or audit["assessment"] != derived
        or audit["normalization"] != proof
        or audit["admissibility_flags"] != flags
    ):
        raise ValueError("Saved assessment differs from raw response replay")
    return audit
