"""Packet-only projection, fixed presence baseline and unfilled human forms.

Transport envelopes and the sealed reference ledger are outside the declared
application/service packet boundary. No lookup of either is possible in adapt().
"""

from __future__ import annotations

import json
import random
from copy import deepcopy
from pathlib import Path

from .storage import digest, events, read, write

QUESTIONS = {
    "Q1": "Who acted? Identify the principal, agent(s) and human where applicable.",
    "Q2": "Under whose authority? Identify the principal-to-actor delegation, scope and any required human decision.",
    "Q3": "What information was available? Identify the request, state/input values and their relation to the decision.",
    "Q4": "Which policy applied? Identify the version and applicable rule linked to the decision.",
    "Q5": "What actions and resources were permitted? Identify tools, resource scope, configuration and preconditions.",
    "Q6": "What action or refusal was issued? Identify actor, request, parameters and disposition; a request does not prove execution.",
    "Q7": "What outcome was independently confirmed? Cite both an executor receipt and a final state observation, including unchanged state for a refusal.",
}
LABELS = {"fully_supported", "partially_supported", "unsupported", "contradictory"}
ROWS = {
    "operator_identity": ["Q1", "Q2"],
    "inputs": ["Q3"],
    "policy_basis": ["Q4"],
    "authorization_envelope": ["Q5"],
    "output_action": ["Q6"],
    "post_condition_state": ["Q7"],
}


def reduce_records(records, deletion):
    output, removed = [], []
    for original in records:
        item = deepcopy(original)
        kind, data = item["kind"], item["data"]
        drop = deletion == "A" and kind in {"authority", "human_decision"}
        if deletion == "O":
            drop = kind == "final_state_check" or (
                kind in {"tool_result", "service_receipt"}
                and not (data.get("status") == "read" and data.get("phase") == "before")
            )
        if drop:
            removed.append({"id": item["id"], "operation": "remove_record"})
            continue
        if deletion == "A" and data.get("reason") == "human_denied":
            del data["reason"]
            removed.append({"id": item["id"], "operation": "remove_field", "path": "data.reason"})
        output.append(item)
    return output, removed


def collect(root):
    records = events(Path(root) / "application-events.jsonl") + events(
        Path(root) / "service-events.jsonl"
    )
    return sorted(records, key=lambda r: (r["time"], r["id"]))


def adapt(packet):
    """Lossless payload mapping, without presence repair or external lookups."""
    mapping = {
        "configuration": "config_snapshot",
        "policy": "policy_snapshot",
        "authority": "agent_message",
        "prompt": "retrieval_result",
        "model_output": "model_generation",
        "tool_request": "tool_call",
        "invalid_arguments": "error",
        "final_state_check": "state_mutation",
    }
    fragments = []
    for record in packet["records"]:
        kind, data = record["kind"], record["data"]
        if kind == "human_decision":
            mapped = "human_approval" if data["decision"] == "approve" else "human_rejection"
        elif kind in {"service_receipt", "tool_result"}:
            mapped = "retrieval_result" if data.get("phase") == "before" else "state_mutation"
        else:
            mapped = mapping[kind]
        fragments.append(
            {
                "fragment_id": record["id"],
                "timestamp": record["time"],
                "kind": mapped,
                "stack_tier": "human" if record["actor"] == "human_user" else packet["tier"],
                "actor_id": record["actor"],
                "payload": deepcopy(data),
                "parent_trace_id": record["parent"],
                "decision_id_hint": packet["packet_id"],
            }
        )
    return {
        "scenario_id": packet["packet_id"],
        "architecture": packet["architecture"],
        "stack_tier": packet["tier"],
        "fragments": fragments,
    }


def baseline(packet):
    """Deliberately weak nonempty-field baseline; no causality or scope checks."""
    records = packet["records"]

    def present(kind, *fields):
        return any(
            r["kind"] == kind and all(r["data"].get(f) not in (None, "", [], {}) for f in fields)
            for r in records
        )

    rules = {
        "operator_identity": present("authority", "principal_id", "delegate", "scope"),
        "inputs": present("prompt", "message"),
        "policy_basis": present("policy", "version", "text"),
        "authorization_envelope": present("configuration", "tools", "resource_scope"),
        "output_action": present("tool_request", "name"),
        "post_condition_state": present("service_receipt", "receipt_id")
        and present("final_state_check", "actual_state"),
    }
    return {key: "fully_fillable" if value else "not_sufficient" for key, value in rules.items()}


def prepare(study, phase):
    study = Path(study)
    index, forms = [], {"reduced": [], "full": []}
    active = (
        {s["run_id"] for s in read(study / "study.json")[phase]}
        if (study / "study.json").exists()
        else None
    )
    for checkpoint in sorted((study / "runs").glob(f"{phase}-*/checkpoint.json")):
        state = read(checkpoint)
        if active is not None and state["run_id"] not in active:
            continue
        if not state.get("ended"):
            continue
        records = collect(checkpoint.parent)
        for condition in (state["deletion"], "full"):
            packet_id = digest({"run": state["run_id"], "condition": condition})[:16]
            visible, deletions = (
                (deepcopy(records), [])
                if condition == "full"
                else reduce_records(records, condition)
            )
            packet = {
                "packet_id": packet_id,
                "architecture": state["architecture"],
                "tier": state["tier"],
                "boundary": "application_and_service_records",
                "records": visible,
            }
            target = study / "packets" / phase / (packet_id + ".json")
            if target.exists() and read(target) != packet:
                raise ValueError("Existing packet changed; preserve the earlier version")
            write(target, packet)
            index.append(
                {
                    "packet_id": packet_id,
                    "run_id": state["run_id"],
                    "condition": condition,
                    "sha256": digest(packet),
                    "deletions": deletions,
                }
            )
            form = {
                "packet_id": packet_id,
                "annotator": None,
                "started": None,
                "ended": None,
                "questions": {
                    q: {
                        "question": text,
                        "label": None,
                        "answer": None,
                        "evidence_ids": [],
                        "reason": None,
                        "exclusion": None,
                    }
                    for q, text in QUESTIONS.items()
                },
            }
            # Prespecified pilot timing sample: the paired within-stack human run.
            # All twelve pilot packets remain available for structural inspection.
            if phase != "pilot" or state["run_id"].endswith("-05"):
                forms["full" if condition == "full" else "reduced"].append(form)
    write(study / f"{phase}-packet-index.json", index)
    for pass_name, rows in forms.items():
        random.Random(231011 if pass_name == "reduced" else 231012).shuffle(rows)
        path = study / "annotations" / f"{phase}-{pass_name}.json"
        if not path.exists():
            write(path, {"origin": "unfilled_human_form", "pass": pass_name, "packets": rows})
    return {"packets": len(index), "author_labels_generated": 0}


def crosswalk(questions):
    result = {}
    for row, keys in ROWS.items():
        labels = [questions[q]["label"] for q in keys]
        result[row] = (
            "contradictory"
            if "contradictory" in labels
            else (labels[0] if len(set(labels)) == 1 else "partially_supported")
        )
    return result


def freeze_annotations(study, phase, pass_name):
    study = Path(study)
    source = study / "annotations" / f"{phase}-{pass_name}.json"
    target = source.with_suffix(".frozen.json")
    if target.exists():
        raise ValueError("Annotations have already been frozen")
    if (
        pass_name == "full"
        and not (study / "annotations" / f"{phase}-reduced.frozen.json").exists()
    ):
        raise ValueError("Freeze the reduced pass before the full pass")
    data = read(source)
    if data.get("origin") not in {"author_entered", "ai_assessed"} or not data["packets"]:
        raise ValueError("Explicitly attributed author or AI annotations are required")
    if (
        data.get("origin") == "ai_assessed"
        and data.get("independent_human_validation") is not False
    ):
        raise ValueError("AI annotations must explicitly disclaim independent human validation")
    expected = {
        r["packet_id"]
        for r in read(study / f"{phase}-packet-index.json")
        if (r["condition"] == "full") == (pass_name == "full")
        and (phase != "pilot" or r["run_id"].endswith("-05"))
    }
    if {r["packet_id"] for r in data["packets"]} != expected or len(data["packets"]) != len(
        expected
    ):
        raise ValueError("Annotation coverage must match the packet population exactly")
    for item in data["packets"]:
        if (
            not item["annotator"]
            or not item["started"]
            or not item["ended"]
            or item["ended"] < item["started"]
        ):
            raise ValueError("Annotator and actual annotation times are required")
        packet = read(study / "packets" / phase / (item["packet_id"] + ".json"))
        ids = {r["id"] for r in packet["records"]}
        if set(item["questions"]) != set(QUESTIONS):
            raise ValueError("All seven questions are required")
        for response in item["questions"].values():
            if response["label"] not in LABELS or not response["answer"] or not response["reason"]:
                raise ValueError("Every label needs an answer and reason")
            if set(response["evidence_ids"]) - ids:
                raise ValueError("Evidence IDs must exist in the exact packet")
            if (
                response["label"] in {"fully_supported", "partially_supported", "contradictory"}
                and not response["evidence_ids"]
            ):
                raise ValueError("Supported/contradictory judgements require packet evidence")
    write(target, {"source_sha256": digest(data), "annotations": data})
    return {"frozen": str(target), "packets": len(data["packets"])}


def render(packet):
    lines = [
        f"# Evidence packet {packet['packet_id']}",
        "",
        "Only the records below constitute this packet. Model narratives are not execution receipts.",
        "",
    ]
    for record in packet["records"]:
        lines += [
            f"## {record['id']} — {record['kind']} — {record['actor']}",
            "",
            "```json",
            json.dumps(record, indent=2),
            "```",
            "",
        ]
    return "\n".join(lines)
