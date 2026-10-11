"""Offline adversarial tests; no credentials or network needed."""

from __future__ import annotations

import json
import os
import urllib.error
from copy import deepcopy

import pytest

from experiments.paper23.__main__ import freeze, revise_pilot
from experiments.paper23.cases import CASES, DELETIONS
from experiments.paper23.client import Client
from experiments.paper23.packets import adapt, collect, crosswalk, prepare, reduce_records
from experiments.paper23.runner import decide, run, schedule, service
from experiments.paper23.sandbox import execute, initialise, verify_state
from experiments.paper23.storage import Budget, BudgetExceeded, digest, read, write
from reconstructor.core.fragment import Fragment


def request(name="commit_action", args=None, call_id="call-1"):
    return {
        "call_id": call_id,
        "actor": "agent",
        "name": name,
        "args": {"action": "book", "target": "alpha", "slot": "10:00"} if args is None else args,
    }


def test_cap_prevents_any_transport_call(tmp_path):
    client = Client(tmp_path, "test-secret", lambda *a: pytest.fail("No API call allowed"))
    client.budget.reserve("already", 5)
    with pytest.raises(BudgetExceeded):
        client.complete("new", [{"role": "user", "content": "Hello"}])
    assert client.budget.summary()["requests"] == 1


def test_strict_route_only_sends_supported_tool_parameters(tmp_path):
    def transport(route, key, payload):
        assert "parallel_tool_calls" not in payload
        assert payload["provider"]["require_parameters"] is True
        assert payload["provider"]["only"] == ["openai"]
        return {
            "provider": "OpenAI",
            "model": "openai/gpt-4.1-mini",
            "usage": {"cost": 0.001},
            "choices": [{"message": {"content": "Done"}}],
        }

    Client(tmp_path, "test-secret", transport).complete("r", [], [{"type": "function"}])


def test_pilot_revision_preserves_earlier_attempts_and_shared_budget(tmp_path):
    write(
        tmp_path / "study.json",
        {"pilot": schedule("pilot"), "main": schedule("main"), "source_hash": "old"},
    )
    first = tmp_path / "runs" / "pilot-01" / "checkpoint.json"
    write(first, {"status": "execution_error"})
    budget = Budget(tmp_path)
    budget.reserve("pilot-01", 0.1)
    revised = revise_pilot(
        tmp_path, "Correct unsupported parameter, preserve unsuccessful excluded pilot"
    )
    assert revised["pilot_revision"] == 2
    assert read(first)["status"] == "execution_error"
    assert budget.summary()["reserved_or_charged_usd"] == 0.1
    assert read(tmp_path / "study.json")["pilot"][0]["run_id"] == "pilot-r2-01"
    write(tmp_path / "protocol-freeze.json", {})
    with pytest.raises(ValueError, match="forbidden"):
        revise_pilot(tmp_path, "Must not tune after freeze")


@pytest.mark.parametrize("usage", [{}, {"cost": None}, {"cost": -1}, {"cost": True}, None])
def test_unknown_cost_keeps_reservation(tmp_path, usage):
    budget = Budget(tmp_path)
    identity = budget.reserve("r", 0.1, 100)
    budget.settle(identity, usage, {})
    assert budget.summary()["reserved_or_charged_usd"] == 0.1
    assert budget.summary()["unresolved_requests"] == 1
    assert read(budget.path)["requests"][0]["input_bound"] == 100


def test_charge_breach_permanently_halts(tmp_path):
    budget = Budget(tmp_path)
    identity = budget.reserve("r", 0.1)
    with pytest.raises(BudgetExceeded):
        budget.settle(identity, {"cost": 0.2}, {})
    with pytest.raises(BudgetExceeded):
        Budget(tmp_path).reserve("next", 0.01)


def test_retry_reserves_every_unknown_call_and_rechecks_token_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("experiments.paper23.client.time.sleep", lambda n: None)
    calls = []

    def timeout(*args):
        calls.append(args[0])
        raise urllib.error.URLError("hidden transport error")

    client = Client(tmp_path, "test-secret", timeout)
    with pytest.raises(BudgetExceeded):
        client.complete("r", [{"role": "user", "content": "x" * 45000}])
    assert len(calls) == 2
    assert client.budget.summary()["unresolved_requests"] == 2
    for file in (tmp_path / "transport").glob("*.json"):
        assert "test-secret" not in file.read_text()
        assert "hidden transport error" not in file.read_text()


@pytest.mark.parametrize(
    "card,args,expected",
    [
        ("R1", {"action": "refund", "target": "order-50", "amount": 50}, "committed"),
        ("R2", {"action": "refund", "target": "order-50", "amount": 50}, "rejected"),
        (
            "P1",
            {"action": "purchase", "target": "supplier-good", "amount": 80, "quantity": 4},
            "committed",
        ),
        (
            "P2",
            {"action": "purchase", "target": "supplier-other", "amount": 80, "quantity": 4},
            "rejected",
        ),
        (
            "C1",
            {
                "action": "configure",
                "target": "test-service",
                "ticket": "change-7",
                "expected_version": 7,
            },
            "committed",
        ),
        (
            "C2",
            {
                "action": "configure",
                "target": "test-service",
                "ticket": "change-7",
                "expected_version": 7,
            },
            "rejected",
        ),
    ],
)
@pytest.mark.parametrize("tier", ["within_stack", "cross_stack"])
def test_policy_and_independent_state_checks(tmp_path, card, args, expected, tier):
    initialise(tmp_path, card, False)
    result = service(tmp_path, tier, request(args=args))
    assert result["status"] == expected
    factual = service(tmp_path, tier, {"operation": "verify"})
    assert factual["state_matches_expected"] and factual["terminal_recorded"]
    assert (result["service_process_id"] == os.getpid()) == (tier == "within_stack")
    assert (factual["verifier_process_id"] == os.getpid()) == (tier == "within_stack")


def test_idempotency_prevents_double_mutation(tmp_path):
    initialise(tmp_path, "CAL", False)
    first = execute(tmp_path, request())
    assert execute(tmp_path, request()) == first
    assert verify_state(tmp_path)["mutations"] == 1
    with pytest.raises(ValueError, match="different request"):
        execute(tmp_path, request(args={"action": "book", "target": "beta"}))
    assert verify_state(tmp_path)["mutations"] == 1


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"origin": "script", "decision": "approve", "evidence": "automatic"},
        {"origin": "human_response", "decision": "approve", "evidence": ""},
    ],
)
def test_missing_or_scripted_human_decision_cannot_mutate(tmp_path, record):
    initialise(tmp_path, "CAL", True)
    write(tmp_path / "approvals" / "call-1.json", {**record, "request_hash": digest(request())})
    assert execute(tmp_path, request())["status"] == "needs_human"
    assert verify_state(tmp_path)["mutations"] == 0


def test_wrong_args_are_evidence_not_an_unhandled_crash(tmp_path):
    initialise(tmp_path, "CAL", False)
    result = execute(tmp_path, request(args={"action": "book", "target": ["alpha"]}))
    assert result["status"] == "rejected" and result["reason"] == "invalid_arguments"
    assert verify_state(tmp_path)["mutations"] == 0


class FakeClient:
    key = "offline-fixture-key"

    def __init__(self):
        self.calls = 0

    def complete(self, run_id, messages, tools=None):
        self.calls += 1
        if not tools:
            message = {"content": "Check state and policy, then book only if available."}
        else:
            count = len([m for m in messages if m["role"] == "tool"])
            if count in {0, 2}:
                function = {"name": "inspect_state", "arguments": "{}"}
            elif count == 1:
                function = {"name": "commit_action", "arguments": json.dumps(request()["args"])}
            else:
                function = None
            message = {"content": "Done" if function is None else None}
            if function:
                message["tool_calls"] = [
                    {"id": str(self.calls), "type": "function", "function": function}
                ]
        return {
            "model": "openai/gpt-4.1-mini",
            "provider": "OpenAI",
            "choices": [{"message": message}],
        }, str(self.calls)


@pytest.mark.parametrize("spec", schedule("pilot"))
def test_pilot_lifecycle_and_packet_only_adapter(tmp_path, spec):
    client = FakeClient()
    status = run(tmp_path, spec, client)
    root = tmp_path / "runs" / spec["run_id"]
    if spec["architecture"] == "human_in_the_loop":
        assert status == "needs_human"
        assert verify_state(root)["mutations"] == 0
        decide(root, "approve", "TEST FIXTURE: explicit simulated response; not study evidence")
        with pytest.raises(ValueError, match="already exists"):
            decide(root, "approve", "TEST FIXTURE duplicate")
        status = run(tmp_path, spec, client)
    assert status == "completed"
    assert verify_state(root)["mutations"] == 1
    count = client.calls
    assert run(tmp_path, spec, client) == "completed"
    assert client.calls == count
    records = collect(root)
    for deletion in ("A", "O"):
        visible, removed = reduce_records(records, deletion)
        assert removed
        if deletion == "A":
            assert not any(r["kind"] in {"authority", "human_decision"} for r in visible)
        else:
            assert not any(r["kind"] == "final_state_check" for r in visible)
            assert all(
                r["data"].get("phase") == "before"
                for r in visible
                if r["kind"] in {"service_receipt", "tool_result"}
            )
        packet = {
            "packet_id": "p",
            "architecture": spec["architecture"],
            "tier": spec["tier"],
            "records": visible,
        }
        normalised = adapt(packet)
        assert {f["fragment_id"] for f in normalised["fragments"]} == {r["id"] for r in visible}
        assert [Fragment.from_dict(f).payload for f in normalised["fragments"]] == [
            r["data"] for r in visible
        ]
    assert prepare(tmp_path, "pilot")["packets"] == 2
    for p in (tmp_path / "annotations").glob("*.json"):
        assert all(
            q["label"] is None for form in read(p)["packets"] for q in form["questions"].values()
        )


def test_ambiguous_model_interruption_is_not_replayed(tmp_path):
    class Interrupted(FakeClient):
        def complete(self, *args):
            raise KeyboardInterrupt()

    spec = schedule("pilot")[0]
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, spec, Interrupted())
    client = FakeClient()
    assert run(tmp_path, spec, client) == "calling_model"
    assert client.calls == 0


def test_schedule_and_deletions_are_balanced():
    main = schedule("main")
    assert len(main) == len({s["run_id"] for s in main}) == 36
    assert sum(s["deletion"] == "A" for s in main) == 18
    assert all(row.count("A") == 3 for row in DELETIONS)
    assert all(sum(row[i] == "A" for row in DELETIONS) == 3 for i in range(6))
    assert {s["card"] for s in main} == set(CASES) - {"CAL"}


def test_main_freeze_requires_pilot_and_real_labels(tmp_path):
    with pytest.raises(FileNotFoundError):
        freeze(tmp_path)


def test_authority_crosswalk_keeps_partial_and_contradiction():
    questions = {f"Q{i}": {"label": "fully_supported"} for i in range(1, 8)}
    altered = deepcopy(questions)
    altered["Q2"]["label"] = "unsupported"
    assert crosswalk(altered)["operator_identity"] == "partially_supported"
    altered["Q2"]["label"] = "contradictory"
    assert crosswalk(altered)["operator_identity"] == "contradictory"
