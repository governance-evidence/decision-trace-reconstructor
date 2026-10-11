"""Projection must not repair evidence using context or assessor judgments."""

from copy import deepcopy

import pytest

from experiments.paper23.storage import digest
from experiments.paper23_typed_replay.adapter import adapt
from reconstructor.core.manifest import FragmentManifest
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
from reconstructor.pipeline import reconstruct


def packet():
    rows = [
        (
            "configuration",
            "system",
            dict(
                tools=[{"function": {"name": "commit_action"}}],
                resource_scope="item",
                human_gate=True,
            ),
        ),
        ("policy", "principal", dict(version="v1", text="Allow item")),
        (
            "authority",
            "principal",
            dict(
                principal_id="p",
                delegate="agent",
                scope={"action": "configure", "policy_version": "v1"},
            ),
        ),
        ("prompt", "requester", dict(message={"content": "Change item"})),
        (
            "tool_request",
            "agent",
            dict(call_id="read", actor="agent", name="inspect_state", args={}),
        ),
        (
            "service_receipt",
            "agent",
            dict(call_id="read", phase="before", status="read", state={"service": "item", "n": 0}),
        ),
        (
            "tool_request",
            "agent",
            dict(call_id="change", actor="agent", name="commit_action", args={"target": "item"}),
        ),
        ("human_decision", "human_user", dict(decision="approve")),
        ("service_receipt", "agent", dict(call_id="change", status="committed")),
        ("final_state_check", "state_verifier", dict(actual_state={"service": "item", "n": 1})),
    ]
    records = [
        dict(id=str(i), time=i, kind=k, actor=a, data=d, parent=None)
        for i, (k, a, d) in enumerate(rows)
    ]
    records[7]["data"]["request_hash"] = digest(records[6]["data"])
    records[7]["parent"] = "change"
    return dict(packet_id="p", architecture="single_agent", tier="within_stack", records=records)


def scores(p):
    m = FragmentManifest.from_dict(adapt(p)[0])
    r = reconstruct(
        m.fragments,
        m.architecture,
        m.stack_tier,
        m.scenario_id,
        evidence_contract=m.evidence_contract,
    )
    return {
        x.property_name: x.category.value
        for x in map_chain_to_schema_aggregate(
            r.chain, m.architecture, m.stack_tier, m.evidence_contract
        )
    }


def test_shape_normalization_keeps_missing_bindings_and_source():
    p = packet()
    old = deepcopy(p)
    m, audit = adapt(p)
    assert p == old
    assert len(audit["records"]) == len(p["records"])
    assert (
        next(f for f in m["fragments"] if f["fragment_id"] == "7")["payload"]["call_id"] == "change"
    )
    outcome = scores(p)
    assert (
        outcome["operator_identity"]
        == outcome["inputs"]
        == outcome["output_action"]
        == "fully_fillable"
    )
    for key in ["policy_basis", "authorization_envelope", "post_condition_state"]:
        assert outcome[key] != "fully_fillable"


@pytest.mark.parametrize("field", ["request_hash", "parent"])
def test_wrong_approval_link_fails(field):
    p = packet()
    if field == "parent":
        p["records"][7][field] = "another-call"
    else:
        p["records"][7]["data"][field] = "wrong-hash"
    assert scores(p)["operator_identity"] != "fully_fillable"


def test_authority_deletion_is_not_repaired():
    p = packet()
    p["records"] = [r for r in p["records"] if r["kind"] not in {"authority", "human_decision"}]
    assert scores(p)["operator_identity"] != "fully_fillable"


def test_outcome_deletion_is_not_repaired_from_model_or_client():
    p = packet()
    echo = deepcopy(p["records"][8])
    echo.update(id="echo", kind="tool_result")
    p["records"] = [r for r in p["records"] if r["id"] not in {"8", "9"}] + [echo]
    with pytest.raises(ValueError, match="Unmatched or conflicting"):
        adapt(p)


def test_exact_echo_omission_has_audit():
    p = packet()
    echo = deepcopy(p["records"][8])
    echo.update(id="echo", kind="tool_result")
    p["records"].append(echo)
    m, audit = adapt(p)
    assert not audit["records"][-1]["included"]
    assert all(f["fragment_id"] != "echo" for f in m["fragments"])


def test_refusal_target_not_invented_from_config():
    p = packet()
    p["records"][6]["data"].update(name="record_refusal", args={"reason": "No"})
    assert scores(p)["inputs"] != "fully_fillable"


def test_topology_does_not_change_projection_scores():
    p = packet()
    before = scores(p)
    p.update(tier="cross_stack", architecture="multi_agent")
    assert scores(p) == before
