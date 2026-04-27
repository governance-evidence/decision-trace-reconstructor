# Worked example: AWS Bedrock AgentCore → Decision Trace Reconstructor (`bedrock_basic_agent`)

This example exercises the Bedrock adapter through the offline path. The input is a direct Bedrock session dump containing one refund-handling interaction with pre-processing, retrieval, orchestration, guardrail, and human approval traces.

## What the trace represents

A single-agent support workflow receives a refund request, checks the internal refund policy, decides to submit the refund, records a policy constraint, and then receives an explicit operator approval before the action completes.

Compared with the OTLP example, this Bedrock example carries stronger native governance evidence because it includes both a guardrail trace and a human approval record.

## Files

```text
examples/bedrock_basic_agent/
├── README.md
├── input/
│   └── sessions.json
└── expected_output/
    ├── fragments.json
    ├── feasibility.json
    └── trace.jsonld
```

## Running it

```bash
decision-trace ingest bedrock \
  --from-file examples/bedrock_basic_agent/input/sessions.json \
  --scenario-id bedrock_basic_agent_demo \
  --architecture single_agent \
  --stack-tier within_stack \
  --out fragments.json

decision-trace reconstruct fragments.json --out out/ --jsonld
diff -ru examples/bedrock_basic_agent/expected_output out
```

## What the adapter produces

The single Bedrock session becomes a manifest that includes:

- one synthetic `config_snapshot` for the session metadata,
- hashed pre-processing and final-response `agent_message` fragments,
- `model_generation` fragments for pre-processing and orchestration,
- one `retrieval_result` from the knowledge-base lookup,
- one `tool_call` plus paired `state_mutation` for the refund POST request,
- one `policy_snapshot` from the guardrail trace,
- one `human_approval` from the return-control block.

This is still not a reasoning-transparent trace: the reconstructor correctly marks the LLM reasoning step as opaque. But unlike vendor-neutral OTLP, Bedrock's native trace blocks can often expose enough policy and approval metadata to make the authorization envelope reconstructable.
