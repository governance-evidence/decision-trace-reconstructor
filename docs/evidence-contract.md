# Evidence visibility and actor attribution

The working mapper separates deployment topology, stored-record visibility and evidence sufficiency. A cross-stack label, multiple record producers, several agents or a human participant no longer imposes a sufficiency downgrade. Nor does a topology label alone diagnose decision diffusion, a missing evidence channel or responsibility ambiguity.

The published Paper23 v0.1.0 results and V5 use separately pinned source. This change does not update that release, its scientific results or the paper. Re-running historical fixtures with the working mapper intentionally produces different structural coverage scores.

## Two explicit assessment contracts

`fragment-coverage-v2` is the backward-compatible default wire route. It classifies which fragment kinds and visible payloads are available. Here, `fully_fillable` means structural coverage, not validated semantic sufficiency. It retains the historical best-unit aggregation and reasoning-opacity convention. CLI JSON and PROV-O output name the assessment contract. Worked examples with the older report shape should be read under this coverage contract.

`decision-evidence-v1` is an opt-in, bounded chain-level contract. It requires typed roles and checks structured obligations across the entire chain, so one good unit cannot hide inconsistent evidence in another. Per-unit reports remain structural coverage. The contract handles structured tool/resource/version binding and outcome-state equality; it does not interpret arbitrary policy prose, authenticate identities, establish legal responsibility, or evaluate task success. It does not implement the proposed fifth `conflicting` category; unresolved conflicts prevent full support and appear in the gap description.

Select the latter with top-level `"evidence_contract": "decision-evidence-v1"` in a fragment manifest. `FragmentManifest` accepts the same field. Direct API consumers must pass `evidence_contract=manifest.evidence_contract` to both `reconstruct()` and `map_chain_to_schema_aggregate()`. The public reconstruction CLI forwards it automatically. Unknown contract names are rejected.

## Independent metadata

Each fragment may carry:

| Field | Values / meaning |
|---|---|
| `stack_tier` | Existing origin/topology field; never evidence visibility. |
| `evidence_visibility` | `visible`, `partial`, `opaque`, `unknown`. Legacy omission defaults to `visible`: stored bytes are readable, not certified complete. |
| `actor_role` | `agent`, `executor`, `observer`, `human`, `principal`, `requester`, `system`, `unknown`; omission is unknown. |
| `evidence_role` | Typed role listed below; omission is acceptable for coverage, but cannot satisfy the typed contract. |
| `decision_id_hint` | Must match the manifest scenario ID for records used by the typed contract. |

The CLI actor inventory reports record producers, declared agents and action issuers separately. Unknown-role producers are not promoted to agents by their names. Model-generation or tool-call producers with no declared role are listed separately as inferred action/model actors. Several distinct action issuers are allowed; conflicting issuer/parameter claims for the same call ID are not. `prov:Agent` retains its broad W3C provenance meaning, including humans and organizations; it is not a count of AI agents.

The adapter is responsible for truthful roles and visibility. These fields are not proof against forged logs. Existing provider adapters continue to emit untyped coverage manifests; they are not silently certified by the new contract.

## Typed payload obligations

All temporal checks use recorded timestamps. All relevant records must be visible and bound to this decision. Duplicate fragment IDs, unknown evidence roles and role/kind mismatches prevent full support. Extra records do not create support merely by their count.

| Evidence role | Fragment kind | Required payload / relation |
|---|---|---|
| `configuration` | `config_snapshot` | `tools` and `resource_scope` lists, Boolean `human_gate`. |
| `policy` | `policy_snapshot` | Nonempty `version` and `text`; version equals the action reference and exists before the action. Competing text under one version is unresolved. |
| `authority` | `agent_message` | Named `principal_id`, `delegate` matching the issuer; principal actor role; prior grant; `scope.tools`, `scope.resources`, `scope.policy_version`. |
| `prompt` | `retrieval_result` | Nonempty `message` before the action. |
| `input_observation` | `retrieval_result` | Action `target`, nonempty `actual_state` object, observed before the action. |
| `model_output` | `model_generation` | Optional model record; not an execution receipt or authority grant. |
| `tool_request` | `tool_call` | `call_id`, `name`, `args` object containing `target`, `policy_version`, and attributable issuer. |
| `human_decision` | `human_approval` or `human_rejection` | Human role, `call_id`, `decision` (`approve`/`deny`), recorded after the proposal and before its receipt when a gate is required. |
| `service_receipt` | `state_mutation` | Executor role, matching `call_id` and `target`, later timestamp, status in `committed/refused/rejected/duplicate`, and nonempty comparable `actual_state`. |
| `final_state_check` | `state_mutation` | Observer role distinct from action issuers and receipt producers; `target`, `after_call_ids` covering target actions, nonempty `actual_state`, at or after the latest receipt. Competing observations or disagreement with that receipt prevent full support. |

Authorization checks whether the supplied grant covers the requested tool/resource/version; a grant for another resource does not provide that support. This is not a complete policy-compliance engine. A recorded refusal or rejected attempt may have fully reconstructable identity, action and outcome. No claim of task correctness follows.

## Examples and verification

```bash
decision-trace reconstruct examples/evidence_contract_case/input/positive.json --out /tmp/dtr-evidence-positive
decision-trace reconstruct examples/evidence_contract_case/input/wrong_receipt.json --out /tmp/dtr-evidence-wrong-receipt
```

The wrong-receipt example retains all record classes but cannot fully support post-condition state. Regression tests cover topology invariance, role counting, explicit visibility, wrong scope/version/call bindings, observer independence, state conflicts across units, malformed fields, untyped extra actions and the public CLI.

The 2026-10-11 Paper23 challenge freezes 20 authored cases and their target labels before implementation. Its runner is `experiments/paper23_evidence_challenge/run.py`. The cases are development conformance requirements, not an independent holdout. Its separate run archive preserves pre-change/current/pinned comparisons, original example expectations and V5 hashes. Ten positive and ten negative target judgments all pass with the typed contract; both the baseline and coverage-only mode pass 10/20. These results establish the implemented bounded checks, not population accuracy or journal readiness.

## Paper23 retained-packet adapter

`experiments.paper23_typed_replay.adapter` provides a versioned packet-only
projection onto `decision-evidence-v1`; the original Paper23 adapter remains
unchanged. Read the adjacent `PROTOCOL.md` before interpreting the comparison.
It preserves original records and transformation provenance, excludes read-only
acquisition calls from material decisions, and does not manufacture missing
policy/scope/outcome bindings. Human call links require both the exact request
hash and its recorded parent call ID.

Replay into a new directory (existing outputs are refused):

```bash
PYTHONPATH=.:src .venv/bin/python -m experiments.paper23_typed_replay.run \
  --source study-data/paper23-20261010-assessor-v5 \
  --output study-data/paper23-20261011-typed-replay-v1
```

The retained 72-packet run gives binary F1 against V5 of 0.8186 for old DTR,
0.9975 for both repaired coverage and the unchanged field-presence baseline,
and 0.5495 for the typed contract. The typed contract is stricter than the
original capture schema and V5 rubric; these figures are not comparative
accuracy estimates. Its 244 non-full verdicts on V5-full rows comprise
72 policy, 72 envelope, 54 outcome and 46 input judgments. All prior V5 files
and delivery archives are verified unchanged. No new inference is used.
