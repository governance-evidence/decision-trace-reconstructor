"""Bounded, typed decision-evidence checks; no topology-based sufficiency rules."""

from __future__ import annotations

import math
from typing import Any

from ..core.chain import DecisionChain
from ..core.fragment import ActorRole, EvidenceVisibility, Fragment, FragmentKind
from .feasibility import FeasibilityCategory, PropertyFeasibility

COVERAGE_CONTRACT = "fragment-coverage-v2"
DECISION_CONTRACT = "decision-evidence-v1"
CONTRACTS = {COVERAGE_CONTRACT, DECISION_CONTRACT}

ROLE_KINDS = {
    "configuration": {FragmentKind.CONFIG_SNAPSHOT},
    "policy": {FragmentKind.POLICY_SNAPSHOT},
    "authority": {FragmentKind.AGENT_MESSAGE},
    "prompt": {FragmentKind.RETRIEVAL_RESULT},
    "input_observation": {FragmentKind.RETRIEVAL_RESULT},
    "model_output": {FragmentKind.MODEL_GENERATION},
    "tool_request": {FragmentKind.TOOL_CALL},
    "service_receipt": {FragmentKind.STATE_MUTATION},
    "final_state_check": {FragmentKind.STATE_MUTATION},
    "human_decision": {FragmentKind.HUMAN_APPROVAL, FragmentKind.HUMAN_REJECTION},
}
PROPERTY_ROLES = {
    "operator_identity": {"authority", "tool_request", "human_decision", "configuration"},
    "inputs": {"prompt", "input_observation", "tool_request"},
    "policy_basis": {"policy", "tool_request"},
    "authorization_envelope": {"configuration", "authority", "tool_request"},
    "output_action": {"tool_request"},
    "post_condition_state": {"tool_request", "service_receipt", "final_state_check"},
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _contains(value: Any, item: Any) -> bool:
    return isinstance(value, list) and _text(item) and item in value


def _target(action: Fragment) -> Any:
    args = action.payload.get("args")
    return args.get("target") if isinstance(args, dict) else None


class Evidence:
    """Records are declarations by the adapter, not authenticated identities."""

    def __init__(self, chain: DecisionChain) -> None:
        self.chain = chain
        self.records = chain.source_fragments
        self.actions = self.role("tool_request")

    def role(self, name: str) -> list[Fragment]:
        return [r for r in self.records if r.evidence_role == name and r.kind in ROLE_KINDS[name]]

    def common(self, prop: str) -> list[str]:
        issues = []
        if not self.actions:
            issues.append("no typed action request anchors the decision")
        ids = [r.fragment_id for r in self.records]
        if len(ids) != len(set(ids)):
            issues.append("duplicate fragment identifiers")
        for r in self.records:
            if r.evidence_role not in ROLE_KINDS:
                issues.append(f"{r.fragment_id}: untyped or unknown evidence role")
                continue
            if r.evidence_role not in PROPERTY_ROLES[prop]:
                continue
            if not math.isfinite(r.timestamp) or not _text(r.actor_id):
                issues.append(f"{r.fragment_id}: missing producer identity or nonfinite time")
            if r.evidence_role == "human_decision":
                expected = "approve" if r.kind == FragmentKind.HUMAN_APPROVAL else "deny"
                if r.payload.get("decision") != expected:
                    issues.append(f"{r.fragment_id}: human decision contradicts record kind")
            if r.kind not in ROLE_KINDS[r.evidence_role]:
                issues.append(f"{r.fragment_id}: evidence role conflicts with fragment kind")
            if r.evidence_visibility != EvidenceVisibility.VISIBLE:
                issues.append(f"{r.fragment_id}: visibility is {r.evidence_visibility.value}")
            if r.decision_id_hint != self.chain.chain_id:
                issues.append(f"{r.fragment_id}: record is not bound to this decision")
        return issues

    def identity(self) -> list[str]:
        issues = []
        configs = self.role("configuration")
        gates = {
            r.payload.get("human_gate")
            for r in configs
            if isinstance(r.payload.get("human_gate"), bool)
        }
        if len(gates) != 1:
            issues.append("human-decision requirement is missing or inconsistent")
        for a in self.actions:
            if a.actor_role not in {ActorRole.AGENT, ActorRole.HUMAN} or not _text(a.actor_id):
                issues.append(f"{a.fragment_id}: action issuer role or identity is unknown")
            grants = [
                r
                for r in self.role("authority")
                if r.payload.get("delegate") == a.actor_id
                and _text(r.payload.get("principal_id"))
                and r.actor_role == ActorRole.PRINCIPAL
                and r.timestamp <= a.timestamp
            ]
            if not grants:
                issues.append(f"{a.fragment_id}: no prior named principal-to-issuer grant")
            if gates == {True}:
                receipts = [
                    r
                    for r in self.role("service_receipt")
                    if r.payload.get("call_id") == a.payload.get("call_id")
                ]
                end = min((r.timestamp for r in receipts), default=float("inf"))
                decisions = [
                    r
                    for r in self.role("human_decision")
                    if r.actor_role == ActorRole.HUMAN
                    and r.payload.get("call_id") == a.payload.get("call_id")
                    and r.payload.get("decision") in ("approve", "deny")
                    and a.timestamp <= r.timestamp <= end
                ]
                if not decisions:
                    issues.append(f"{a.fragment_id}: no timely call-specific human decision")
                elif len({r.payload["decision"] for r in decisions}) > 1:
                    issues.append(f"{a.fragment_id}: conflicting human decisions")
        return issues

    def inputs(self) -> list[str]:
        issues = []
        first = min((a.timestamp for a in self.actions), default=float("-inf"))
        if not any(
            _text(r.payload.get("message")) and r.timestamp <= first for r in self.role("prompt")
        ):
            issues.append("no recorded request before the action")
        for a in self.actions:
            matches = [
                r
                for r in self.role("input_observation")
                if _text(_target(a))
                and r.payload.get("target") == _target(a)
                and isinstance(r.payload.get("actual_state"), dict)
                and r.payload["actual_state"]
                and r.timestamp < a.timestamp
            ]
            if not matches:
                issues.append(f"{a.fragment_id}: no target-specific pre-action state")
        return issues

    def policy(self) -> list[str]:
        issues = []
        for a in self.actions:
            version = a.payload.get("policy_version")
            policies = [
                r
                for r in self.role("policy")
                if _text(version)
                and r.payload.get("version") == version
                and _text(r.payload.get("text"))
                and r.timestamp <= a.timestamp
            ]
            if not policies:
                issues.append(f"{a.fragment_id}: referenced policy version unavailable")
            elif len({r.payload["text"] for r in policies}) > 1:
                issues.append(f"{a.fragment_id}: conflicting text for one policy version")
        return issues

    def envelope(self) -> list[str]:
        issues = []
        for a in self.actions:
            name, target = a.payload.get("name"), _target(a)
            configs = [
                r
                for r in self.role("configuration")
                if _contains(r.payload.get("tools"), name)
                and _contains(r.payload.get("resource_scope"), target)
                and r.timestamp <= a.timestamp
            ]
            if not configs:
                issues.append(f"{a.fragment_id}: tool/resource not evidenced by configuration")
            scopes = [
                r.payload.get("scope")
                for r in self.role("authority")
                if r.payload.get("delegate") == a.actor_id
                and r.timestamp <= a.timestamp
                and r.actor_role == ActorRole.PRINCIPAL
                and _text(r.payload.get("principal_id"))
            ]
            if not any(
                isinstance(s, dict)
                and _contains(s.get("tools"), name)
                and _contains(s.get("resources"), target)
                and _text(a.payload.get("policy_version"))
                and s.get("policy_version") == a.payload.get("policy_version")
                for s in scopes
            ):
                issues.append(f"{a.fragment_id}: no applicable tool/resource/version grant")
        return issues

    def output(self) -> list[str]:
        issues = []
        seen: dict[str, tuple[str, dict[str, Any]]] = {}
        for a in self.actions:
            d = a.payload
            if (
                not all(_text(d.get(k)) for k in ("call_id", "name"))
                or not isinstance(d.get("args"), dict)
                or not _text(a.actor_id)
            ):
                issues.append(f"{a.fragment_id}: incomplete action identity or parameters")
                continue
            call = d["call_id"]
            signature = a.actor_id, d
            if call in seen and seen[call] != signature:
                issues.append(f"{a.fragment_id}: conflicting issuer or parameters for call {call}")
            seen[call] = signature
        return issues

    def outcome(self) -> list[str]:
        # A receipt cannot resolve an ambiguous or incomplete request binding.
        issues = self.output()
        receipts = self.role("service_receipt")
        issuer_ids = {a.actor_id for a in self.actions}
        targets: dict[str, list[tuple[Fragment, Fragment]]] = {}
        for a in self.actions:
            call, target = a.payload.get("call_id"), _target(a)
            matches = [
                r
                for r in receipts
                if _text(call)
                and _text(target)
                and r.payload.get("call_id") == call
                and r.payload.get("target") == target
                and r.actor_role == ActorRole.EXECUTOR
                and r.timestamp >= a.timestamp
                and r.payload.get("status") in ("committed", "refused", "rejected", "duplicate")
            ]
            if not matches:
                issues.append(f"{a.fragment_id}: no correctly linked, later executor receipt")
                continue
            if any(
                any(
                    r.payload.get(k) != matches[0].payload.get(k)
                    for k in ("status", "target", "actual_state")
                )
                for r in matches[1:]
            ):
                issues.append(f"{a.fragment_id}: conflicting receipts")
            targets.setdefault(str(target), []).append((a, max(matches, key=lambda r: r.timestamp)))
        for target, pairs in targets.items():
            calls = {a.payload["call_id"] for a, _ in pairs}
            latest = max((r for _, r in pairs), key=lambda r: r.timestamp)
            observers = [
                r
                for r in self.role("final_state_check")
                if r.payload.get("target") == target
                and r.actor_role == ActorRole.OBSERVER
                and r.actor_id not in issuer_ids
                and r.actor_id not in {receipt.actor_id for receipt in receipts}
                and r.timestamp >= latest.timestamp
                and isinstance(r.payload.get("after_call_ids"), list)
                and all(call in r.payload["after_call_ids"] for call in calls)
                and isinstance(r.payload.get("actual_state"), dict)
                and r.payload["actual_state"]
            ]
            if not observers:
                issues.append(
                    f"{target}: no independent later state observation covering all calls"
                )
                continue
            state = observers[0].payload["actual_state"]
            if any(r.payload["actual_state"] != state for r in observers[1:]):
                issues.append(f"{target}: conflicting final-state observations")
            receipt_state = latest.payload.get("actual_state")
            if not isinstance(receipt_state, dict) or not receipt_state:
                issues.append(f"{target}: latest receipt lacks comparable outcome state")
            elif state != receipt_state:
                issues.append(f"{target}: final state disagrees with latest receipt")
        return issues


def assess_decision_evidence(
    chain: DecisionChain, coverage: list[PropertyFeasibility]
) -> list[PropertyFeasibility]:
    evidence = Evidence(chain)
    checks = dict(
        operator_identity=evidence.identity,
        inputs=evidence.inputs,
        policy_basis=evidence.policy,
        authorization_envelope=evidence.envelope,
        output_action=evidence.output,
        post_condition_state=evidence.outcome,
    )
    output = []
    for original in coverage:
        prop = original.property_name
        if prop not in checks:
            output.append(original)
            continue
        issues = evidence.common(prop) + checks[prop]()
        if not issues:
            category, confidence = FeasibilityCategory.FULLY_FILLABLE, 1.0
        elif any(r.evidence_role in PROPERTY_ROLES[prop] for r in evidence.records):
            category, confidence = FeasibilityCategory.PARTIALLY_FILLABLE, 0.5
        else:
            category, confidence = FeasibilityCategory.STRUCTURALLY_UNFILLABLE, 0.0
        output.append(
            PropertyFeasibility(
                prop, category, original.value, "; ".join(dict.fromkeys(issues)) or None, confidence
            )
        )
    return output
