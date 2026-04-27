# Worked example: Replit DROP DATABASE incident (July 2025)

This example walks one named-incident reconstruction end-to-end. It shows what a **public-record reader** can deliver as input, what the reconstructor returns (the output), and how the per-property feasibility profile maps onto the **DEMM** rubric.

It is one of the three named incidents reconstructed in the companion method paper. The same fragment manifest is used by the test suite to pin reproducibility.

## What the public record establishes

A Replit Agent session executed a destructive SQL command against a production database during an authorized session. Replit later published an official response cataloguing platform mitigations (rollback windows, scope-locked agent permissions, deploy guards on destructive operations, updated agent default-allow policies). The catalogue of subsequent mitigations is itself diagnostic: each mitigation closes a property-level gap the original session left open.

## What this example infers

The example does **not** claim to reconstruct the actual session. It reconstructs a fragment manifest consistent with what a public-record reader can recover: a user prompt (cross-stack), a model generation (opaque internal reasoning), a tool call carrying the destructive SQL statement, and a state mutation observed on the production database. Properties not disclosed publicly (policy basis, authorization envelope) are absent from the manifest, so the reconstructor reports them as `structurally_unfillable` — exactly as it should.

## Files

```
examples/replit_drop_database/
├── README.md                           ← you are here
├── run.py                              ← driver: load → reconstruct → emit
├── input/
│   └── fragments.json                  ← evidence manifest (4 fragments)
└── expected_output/
    ├── feasibility.json                ← per-property feasibility report
    ├── trace.jsonld                    ← W3C PROV-O JSON-LD trace
    └── summary.txt                     ← human-readable narrative
```

## Running it

```bash
cd examples/replit_drop_database
python run.py                           # writes ./out/{feasibility,trace,summary}
diff -ru expected_output out            # should be empty
```

The reference outputs (`expected_output/`) ship with the package and are what `pytest` verifies against. If the diff is non-empty after a code change, either you found a regression or you intentionally changed behaviour (and need to refresh the references).

## Walking the manifest

`input/fragments.json` is exactly what a governance-grade fragments input looks like. Excerpt (truncated):

```json
{
  "scenario_id": "replit_drop_database_2025_07",
  "architecture": "single_agent",
  "stack_tier": "cross_stack",
  "fragments": [
    {
      "fragment_id": "replit_f000",
      "timestamp": 1720000000.0,
      "kind": "agent_message",
      "stack_tier": "cross_stack",
      "actor_id": "user_principal",
      "payload": {"content": "user prompt requesting data cleanup (public report)"},
      "parent_trace_id": null,
      "decision_id_hint": null
    },
    { "fragment_id": "replit_f001", "kind": "model_generation", "...": "..." },
    { "fragment_id": "replit_f002", "kind": "tool_call",        "...": "..." },
    { "fragment_id": "replit_f003", "kind": "state_mutation",   "...": "..." }
  ]
}
```

Four fragments. No `policy_snapshot`, no `config_snapshot`, no `human_approval`. That absence is the input to the analysis — the reconstructor will report exactly what is missing.

## Walking the output

### `expected_output/feasibility.json`

The per-property feasibility report. Quote:

```json
{
  "scenario_id": "replit_drop_database_2025_07",
  "completeness_pct": 57.1,
  "dominant_mode": 3,
  "dominant_break": "evidence_fragmentation",
  "feasibility_counts": {
    "fully_fillable": 2,
    "partially_fillable": 2,
    "structurally_unfillable": 2,
    "opaque": 1
  },
  "per_property": [
    { "property": "inputs",                 "category": "partially_fillable" },
    { "property": "policy_basis",           "category": "structurally_unfillable" },
    { "property": "operator_identity",      "category": "fully_fillable" },
    { "property": "authorization_envelope", "category": "structurally_unfillable" },
    { "property": "reasoning_trace",        "category": "opaque" },
    { "property": "output_action",          "category": "fully_fillable" },
    { "property": "post_condition_state",   "category": "partially_fillable" }
  ]
}
```

Reading it as a DEMM auditor would:

- `reasoning_trace = opaque` — by design; the LLM step is substituted by an authorization envelope.
- `authorization_envelope = structurally_unfillable` — but the envelope itself is **not** in the fragment manifest. This is the central finding: the deployment did not record the constraint surface that defines what the agent was authorized to do.
- `policy_basis = structurally_unfillable` — no policy snapshot was captured, so the auditor cannot reconstruct under what governance regime the destructive mutation was authorized.
- `inputs` and `post_condition_state` are `partially_fillable` because the cross-stack boundary discards full payload visibility.
- `output_action = fully_fillable` — the destructive SQL statement is in the public record.
- `operator_identity = fully_fillable` — the user prompt is attributable.

The dominant-break attribution is `evidence_fragmentation` (mode 3): the governance-relevant evidence is split across channels not all audited.

### `expected_output/trace.jsonld`

The same data expressed as a W3C PROV-O graph. Loadable in any PROV-aware tool:

```python
from rdflib import Graph
g = Graph()
g.parse("expected_output/trace.jsonld", format="json-ld")

# How many fragments touched the destructive output_action?
q = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX demm: <https://decisiontrace.org/demm/v1#>
PREFIX schema: <https://decisiontrace.org/schema/v1#>
SELECT ?frag WHERE {
  ?unit a demm:DecisionUnit ;
        prov:wasInfluencedBy ?frag .
  ?feas demm:property schema:output_action ;
        demm:category "fully_fillable" .
}
"""
for row in g.query(q):
    print(row)
```

### `expected_output/summary.txt`

The same information as plain text — useful for inclusion in audit deliverables that don't render JSON.

## Where this example fits in DEMM

Under the method specification, the auditor's question "under what governance regime was this destructive mutation authorized?" is exactly the question this manifest **cannot answer at the property level**. The reconstructability profile (`policy_basis`, `authorization_envelope` both `structurally_unfillable`) places this deployment at **DEMM Level 1 (ad-hoc)** for the property classes the question tests, irrespective of what level it might reach for other property classes.

The point of the reconstructor is not that this reconstruction is novel — Replit's own engineering response identified the same gaps and shipped mitigations that close them. The point is that the gap profile is reproducible from the public record alone, and that the same diagnostic fits across other single-agent cross-stack incidents (Cursor, Claude Code DataTalks.Club — see `src/reconstructor/synthetic/named_incidents.py`).
