"""Packet-only Paper23 projection onto decision-evidence-v1.

No assessor labels, sibling packet, run ledger or inferred grant scope enters
this adapter. The audit retains original records and every transformation.
"""

from copy import deepcopy

from experiments.paper23.packets import adapt as legacy_adapt
from experiments.paper23.storage import digest

VERSION = "paper23-typed-adapter-v1"
ROLES = {
    "configuration": "system",
    "policy": "principal",
    "authority": "principal",
    "prompt": "requester",
    "model_output": "agent",
    "tool_request": "agent",
    "service_receipt": "executor",
    "final_state_check": "observer",
    "human_decision": "human",
}


def state_target(state):
    """Only explicit sandbox entity identifiers, never configuration scope."""
    if not isinstance(state, dict):
        return None
    values = [state[k] for k in ("service", "order", "supplier", "room") if k in state]
    return values[0] if len(values) == 1 and isinstance(values[0], str) else None


def adapt(packet):
    source = deepcopy(packet)
    manifest = legacy_adapt(source)
    manifest["evidence_contract"] = "decision-evidence-v1"
    fragments, audit = [], []
    records = source["records"]
    requests = [r for r in records if r["kind"] == "tool_request"]
    receipts = [r for r in records if r["kind"] == "service_receipt"]
    for record, fragment in zip(records, manifest["fragments"], strict=True):
        kind, data = record["kind"], fragment["payload"]
        changes, supporting = [], []
        row = {
            "record_id": record["id"],
            "source_record": record,
            "changes": changes,
            "supporting_record_ids": supporting,
            "included": True,
        }
        audit.append(row)
        if kind == "tool_result":
            if not any(r["data"] == data for r in receipts):
                raise ValueError(
                    "Unmatched or conflicting client result needs an explicit contract"
                )
            row.update(included=False, reason="Exact client echo of a retained service receipt")
            continue
        if kind == "tool_request" and data.get("name") == "inspect_state":
            if data.get("args") != {}:
                raise ValueError("Unexpected arguments to read-only inspect_state")
            row.update(
                included=False, reason="Read-only acquisition call, not a material decision attempt"
            )
            continue
        if kind not in ROLES:
            raise ValueError(f"Unsupported record kind: {kind}; do not silently omit")
        fragment.update(actor_role=ROLES[kind], evidence_role=kind, evidence_visibility="visible")
        if kind == "configuration":
            tools = data.get("tools")
            if isinstance(tools, list) and all(
                isinstance(t, dict) and isinstance(t.get("function", {}).get("name"), str)
                for t in tools
            ):
                data["tools"] = [t["function"]["name"] for t in tools]
                changes.append("tools[].function.name -> tools[]")
            if isinstance(data.get("resource_scope"), str):
                data["resource_scope"] = [data["resource_scope"]]
                changes.append("scalar resource_scope -> singleton list")
        elif kind == "prompt" and isinstance(data.get("message"), dict):
            data["message"] = data["message"].get("content")
            changes.append("message.content -> message")
        elif kind == "human_decision":
            matches = [
                r
                for r in requests
                if digest(r["data"]) == data.get("request_hash")
                and r["data"].get("call_id") == record.get("parent")
            ]
            if len(matches) == 1:
                data["call_id"] = matches[0]["data"]["call_id"]
                supporting.append(matches[0]["id"])
                changes.append("exact request hash AND parent call ID -> call_id")
        elif kind == "service_receipt":
            if data.get("phase") == "before" and data.get("status") == "read":
                fragment.update(evidence_role="input_observation", kind="retrieval_result")
                data["actual_state"] = deepcopy(data.get("state"))
                target = state_target(data.get("state"))
                if target:
                    data["target"] = target
                changes.append("pre-action state -> actual_state; explicit state entity -> target")
            else:
                matches = [r for r in requests if r["data"].get("call_id") == data.get("call_id")]
                if len(matches) == 1 and matches[0]["data"].get("args", {}).get("target"):
                    data["target"] = matches[0]["data"]["args"]["target"]
                    supporting.append(matches[0]["id"])
                    changes.append("unique call_id join -> explicit request target")
        elif kind == "final_state_check":
            target = state_target(data.get("actual_state"))
            if target:
                data["target"] = target
                changes.append("explicit actual_state entity -> target")
        fragments.append(fragment)
    manifest["fragments"] = fragments
    return manifest, {
        "adapter": VERSION,
        "packet_sha256": digest(packet),
        "records": audit,
        "policy": "Missing policy references, grant scope, refusal targets, receipt state and final-call bindings remain missing.",
    }
