"""Evidence invariants independent of topology, actor spelling and unit boundaries."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from reconstructor.cli import main
from reconstructor.core.actors import actor_inventory
from reconstructor.core.chain import DecisionChain, DecisionUnit
from reconstructor.core.fragment import (
    ActorRole,
    EvidenceVisibility,
    Fragment,
    FragmentKind,
    StackTier,
)
from reconstructor.core.manifest import FragmentManifest
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.pipeline import reconstruct


def manifest() -> FragmentManifest:
    data = [
        (
            "configuration",
            "config_snapshot",
            "sys",
            "system",
            dict(tools=["write"], resource_scope=["item"], human_gate=False),
        ),
        (
            "policy",
            "policy_snapshot",
            "owner",
            "principal",
            dict(version="v7", text="Write item under delegated scope."),
        ),
        (
            "authority",
            "agent_message",
            "owner",
            "principal",
            dict(
                principal_id="p",
                delegate="worker",
                scope=dict(tools=["write"], resources=["item"], policy_version="v7"),
            ),
        ),
        ("prompt", "retrieval_result", "user", "requester", dict(message="Write item.")),
        (
            "input_observation",
            "retrieval_result",
            "reader",
            "observer",
            dict(target="item", actual_state={"n": 0}),
        ),
        (
            "tool_request",
            "tool_call",
            "worker",
            "agent",
            dict(call_id="op", name="write", args={"target": "item", "n": 1}, policy_version="v7"),
        ),
        (
            "service_receipt",
            "state_mutation",
            "service",
            "executor",
            dict(call_id="op", target="item", status="committed", actual_state={"n": 1}),
        ),
        (
            "final_state_check",
            "state_mutation",
            "verifier",
            "observer",
            dict(after_call_ids=["op"], target="item", actual_state={"n": 1}),
        ),
    ]
    fragments = [
        Fragment(
            str(i),
            float(i),
            FragmentKind(kind),
            StackTier.CROSS_STACK,
            actor,
            payload,
            decision_id_hint="case",
            actor_role=ActorRole(role),
            evidence_role=erole,
        )
        for i, (erole, kind, actor, role, payload) in enumerate(data)
    ]
    return FragmentManifest(
        "case", "multi_agent", StackTier.CROSS_STACK, fragments, "decision-evidence-v1"
    )


def scores(m: FragmentManifest) -> dict[str, str]:
    r = reconstruct(
        m.fragments,
        m.architecture,
        m.stack_tier,
        m.scenario_id,
        evidence_contract=m.evidence_contract,
    )
    return {
        p.property_name: p.category.value
        for p in map_chain_to_schema_aggregate(
            r.chain, m.architecture, m.stack_tier, m.evidence_contract
        )
    }


@pytest.mark.parametrize("architecture", ["single_agent", "multi_agent", "human_in_the_loop"])
@pytest.mark.parametrize("tier", [StackTier.WITHIN_STACK, StackTier.CROSS_STACK])
def test_topology_and_architecture_do_not_change_supported_evidence(
    architecture: str, tier: StackTier
) -> None:
    m = replace(manifest(), architecture=architecture, stack_tier=tier)
    assert all(v == "fully_fillable" for k, v in scores(m).items() if k != "reasoning_trace")


@pytest.mark.parametrize(
    "visibility,category",
    [
        ("visible", "fully_fillable"),
        ("partial", "partially_fillable"),
        ("unknown", "partially_fillable"),
        ("opaque", "structurally_unfillable"),
    ],
)
@pytest.mark.parametrize("tier", [StackTier.WITHIN_STACK, StackTier.CROSS_STACK])
def test_explicit_visibility_controls_fragment_coverage(
    visibility: str, category: str, tier: StackTier
) -> None:
    f = Fragment(
        "x",
        1,
        FragmentKind.RETRIEVAL_RESULT,
        tier,
        "source",
        {"value": 1},
        evidence_visibility=EvidenceVisibility(visibility),
    )
    m = FragmentManifest("x", "single_agent", tier, [f])
    assert scores(m)["inputs"] == category


def test_observers_and_producers_are_not_counted_as_agents() -> None:
    m = manifest()
    inventory = actor_inventory(m.fragments)
    assert inventory["declared_agents"] == ["worker"]
    assert inventory["action_issuers"] == ["worker"]
    assert len(inventory["record_producers"]) == 7
    assert inventory["inferred_action_or_model_actors"] == []
    before = scores(m)
    added = [
        replace(m.fragments[-1], fragment_id=f"observer-{i}", actor_id=f"person-{i}")
        for i in range(12)
    ]
    assert scores(replace(m, fragments=m.fragments + added)) == before


def test_unknown_record_producers_are_not_inferred_from_names() -> None:
    f = Fragment("x", 1, FragmentKind.CONFIG_SNAPSHOT, StackTier.WITHIN_STACK, "agent-123")
    assert actor_inventory([f])["inferred_action_or_model_actors"] == []


def test_wire_contract_preserves_new_metadata_and_legacy_shape() -> None:
    m = manifest()
    assert FragmentManifest.from_dict(m.to_dict()) == m
    old = Fragment("x", 1, FragmentKind.CONFIG_SNAPSHOT, StackTier.WITHIN_STACK, "system").to_dict()
    assert "actor_role" not in old and "evidence_visibility" not in old
    assert Fragment.from_dict(old).to_dict() == old
    for field, value in [
        ("actor_role", "magical"),
        ("evidence_visibility", "perfect"),
        ("evidence_role", {}),
    ]:
        with pytest.raises(ValueError):
            Fragment.from_dict({**old, field: value})
    with pytest.raises(ValueError):
        replace(m, evidence_contract="misspelled-contract")


@pytest.mark.parametrize(
    "role,key,value,target",
    [
        (
            "authority",
            "scope",
            {"tools": ["write"], "resources": ["elsewhere"], "policy_version": "v7"},
            "authorization_envelope",
        ),
        ("policy", "version", "v0", "policy_basis"),
        ("service_receipt", "call_id", "another-call", "post_condition_state"),
        ("service_receipt", "status", {}, "post_condition_state"),
        ("final_state_check", "after_call_ids", [], "post_condition_state"),
        ("final_state_check", "actual_state", {}, "post_condition_state"),
        ("tool_request", "args", None, "output_action"),
        ("authority", "principal_id", None, "operator_identity"),
    ],
)
def test_present_but_inadequate_records_are_not_full(
    role: str, key: str, value: object, target: str
) -> None:
    m = deepcopy(manifest())
    next(f for f in m.fragments if f.evidence_role == role).payload[key] = value
    assert scores(m)[target] != "fully_fillable"


def test_stale_and_self_observed_outcomes_are_not_independent() -> None:
    m = manifest()
    for replacement in [
        replace(m.fragments[-1], timestamp=4),
        replace(m.fragments[-1], actor_id="worker"),
        replace(m.fragments[-1], actor_id="service"),
        replace(m.fragments[-1], actor_role=ActorRole.EXECUTOR),
    ]:
        assert (
            scores(replace(m, fragments=m.fragments[:-1] + [replacement]))["post_condition_state"]
            != "fully_fillable"
        )


def test_later_good_unit_cannot_hide_a_conflicting_state() -> None:
    m = manifest()
    bad = replace(
        m.fragments[-1],
        fragment_id="contradiction",
        payload={**m.fragments[-1].payload, "actual_state": {"n": 2}},
    )
    fragments = m.fragments + [bad]
    for units in [
        [DecisionUnit("one", fragments, "initial", 1)],
        [DecisionUnit(str(i), [f], "initial", 1) for i, f in enumerate(fragments)],
    ]:
        chain = DecisionChain("case", units, fragments)
        result = map_chain_to_schema_aggregate(
            chain, m.architecture, m.stack_tier, m.evidence_contract
        )
        assert (
            next(p for p in result if p.property_name == "post_condition_state").category.value
            != "fully_fillable"
        )


def test_duplicate_action_binding_is_ambiguous_but_distinct_issuers_are_allowed() -> None:
    m = manifest()
    a = m.fragments[5]
    duplicate = replace(a, fragment_id="another-action", actor_id="worker-2")
    assert (
        scores(replace(m, fragments=m.fragments + [duplicate]))["output_action"] != "fully_fillable"
    )
    independent = replace(duplicate, payload={**a.payload, "call_id": "op2"})
    assert (
        scores(replace(m, fragments=m.fragments + [independent]))["output_action"]
        == "fully_fillable"
    )


def test_untyped_extra_action_cannot_bypass_typed_contract() -> None:
    m = manifest()
    hidden = replace(m.fragments[5], fragment_id="untyped-action", evidence_role=None)
    assert scores(replace(m, fragments=m.fragments + [hidden]))["output_action"] != "fully_fillable"


def test_partial_observation_is_not_repaired_by_presence_of_a_receipt() -> None:
    m = manifest()
    f = replace(m.fragments[-1], evidence_visibility=EvidenceVisibility.PARTIAL)
    assert (
        scores(replace(m, fragments=m.fragments[:-1] + [f]))["post_condition_state"]
        != "fully_fillable"
    )


def test_human_decision_must_bind_to_this_request() -> None:
    m = deepcopy(manifest())
    m.fragments[0].payload["human_gate"] = True
    human = Fragment(
        "human",
        5.5,
        FragmentKind.HUMAN_APPROVAL,
        StackTier.HUMAN,
        "operator",
        {"decision": "approve", "call_id": "op"},
        decision_id_hint="case",
        actor_role=ActorRole.HUMAN,
        evidence_role="human_decision",
    )
    assert (
        scores(replace(m, fragments=m.fragments + [human]))["operator_identity"] == "fully_fillable"
    )
    for payload in [{"decision": "approve", "call_id": "wrong"}, {"decision": {}, "call_id": "op"}]:
        assert (
            scores(replace(m, fragments=m.fragments + [replace(human, payload=payload)]))[
                "operator_identity"
            ]
            != "fully_fillable"
        )


def test_decision_binding_cannot_be_borrowed_from_another_trace() -> None:
    m = manifest()
    wrong = replace(m.fragments[-1], decision_id_hint="other-decision")
    assert (
        scores(replace(m, fragments=m.fragments[:-1] + [wrong]))["post_condition_state"]
        != "fully_fillable"
    )


def test_cli_reports_contract_and_actor_population(tmp_path: Path) -> None:
    m = manifest()
    source = tmp_path / "manifest.json"
    source.write_text(m.to_json())
    dest = tmp_path / "output"
    assert main(["reconstruct", str(source), "--out", str(dest), "--jsonld"]) == 0
    report = json.loads((dest / "feasibility.json").read_text())
    assert report["evidence_contract"] == "decision-evidence-v1"
    assert report["actor_inventory"]["declared_agents"] == ["worker"]
    assert {p["property"]: p["category"] for p in report["per_property"]} == scores(m)


def test_only_explicit_opacity_supports_a_channel_gap_diagnosis() -> None:
    for tier in (StackTier.WITHIN_STACK, StackTier.CROSS_STACK):
        f = Fragment(
            "opaque",
            1,
            FragmentKind.RETRIEVAL_RESULT,
            tier,
            "reader",
            evidence_visibility=EvidenceVisibility.OPAQUE,
        )
        report = reconstruct([f], "multi_agent", tier)
        assert report.dominant_mode() is not None
        assert report.dominant_mode().value == 3


@pytest.mark.parametrize(
    "change", [dict(actor_id=""), dict(timestamp=float("inf")), dict(timestamp=float("nan"))]
)
def test_unknown_observer_or_nonfinite_time_cannot_establish_outcome(
    change: dict[str, object],
) -> None:
    m = manifest()
    observer = replace(m.fragments[-1], **change)
    assert (
        scores(replace(m, fragments=m.fragments[:-1] + [observer]))["post_condition_state"]
        != "fully_fillable"
    )


def test_conflicting_call_cannot_gain_full_outcome_from_one_receipt() -> None:
    m = manifest()
    rival = replace(m.fragments[5], fragment_id="rival", actor_id="rival-agent")
    assert (
        scores(replace(m, fragments=m.fragments + [rival]))["post_condition_state"]
        != "fully_fillable"
    )
