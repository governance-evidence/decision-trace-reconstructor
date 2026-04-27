# Worked example: OpenTelemetry GenAI OTLP → Decision Trace Reconstructor (`otlp_basic_agent`)

This example exercises the new **OpenTelemetry GenAI OTLP adapter** via the offline path. The input is a small but plausible flattened OTLP export: one LLM span with user/system events, one internal retrieval step, one external web-search tool call, and one within-stack CRM writeback.

## What the trace represents

A single-agent support workflow answers a policy question about enterprise returns. The agent:

1. receives the user question and a system instruction,
2. checks an internal RAG index,
3. performs one cross-stack web search for freshness,
4. writes the drafted answer context back into an internal CRM record.

Architecturally this example is **single-agent, within-stack by default**, with one deliberate per-fragment elevation to `cross_stack` on the external web-search call.

## Files

```text
examples/otlp_basic_agent/
├── README.md
├── input/
│   └── spans.json
└── expected_output/
    ├── fragments.json
    ├── feasibility.json
    └── trace.jsonld
```

## Running it

```bash
decision-trace ingest otlp \
  --from-file examples/otlp_basic_agent/input/spans.json \
  --scenario-id otlp_basic_agent_demo \
  --architecture single_agent \
  --stack-tier within_stack \
  --within-stack-services agent-api,internal-rag,internal-crm \
  --state-mutation-tools "(update|write|delete|drop|exec)" \
  --out fragments.json

decision-trace reconstruct fragments.json --out out/ --jsonld
diff -ru examples/otlp_basic_agent/expected_output out
```

## What the adapter produces

The four OTLP spans become 7 fragments:

| OTLP span | Adapter rule | Fragment(s) |
| --- | --- | --- |
| `chat gpt-4o` | `gen_ai.operation.name=chat` + message events | `model_generation` + 2 `agent_message` |
| `retrieve internal docs` | operator override `demm.fragment_kind=retrieval_result` | `retrieval_result` |
| `search web` | `execute_tool` + external `server.address` | `tool_call` with `stack_tier: cross_stack` |
| `write crm note` | `execute_tool` + state-mutation regex | `tool_call` + `state_mutation` |

By default the adapter hashes message content and tool payloads rather than persisting raw content. The manifest therefore preserves evidence shape without leaking the exact text into the fixture.

## Reconstruction outcome

| Metric | Value |
| --- | --- |
| Decision units detected | 4 |
| Reconstruction completeness | **71.4%** |
| Dominant structural break | `evidence_fragmentation` |

Per-property feasibility:

| Property | Category | Notes |
| --- | --- | --- |
| inputs | `fully_fillable` | user/system events and retrieval evidence are present |
| policy_basis | `structurally_unfillable` | no policy snapshot was recorded |
| operator_identity | `fully_fillable` | actor id is explicit on all fragments |
| authorization_envelope | `structurally_unfillable` | no config snapshot / approval boundary was recorded |
| reasoning_trace | `opaque` | model generation uses the opaque substitution |
| output_action | `fully_fillable` | tool calls are explicit |
| post_condition_state | `fully_fillable` | CRM writeback emits paired `state_mutation` |

This is the intended "vanilla OTLP" outcome: good operational evidence, but missing policy/config artifacts that many deployments still fail to emit.
