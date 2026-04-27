# Worked example: Generic JSONL fallback → Decision Trace Reconstructor (`generic_jsonl_basic_agent`)

This example exercises the Generic JSONL fallback adapter on a fictional internal orchestrator (`HomegrownAgent`) with a small YAML mapping config:

- one prompt and one model response from the main agent loop
- one cross-stack retrieval record emitted by a custom search worker
- one `write_report` tool call with absorbed `tool_result`
- one explicit human approval from a reviewer
- one operator-chosen redaction on `metadata.session_token`

Validate the mapping against the sample log with:

```bash
decision-trace validate generic-jsonl \
  --mapping examples/generic_jsonl_basic_agent/input/mapping.yaml \
  --sample-from examples/generic_jsonl_basic_agent/input/agent_log.jsonl
```

Generate the pinned manifest with:

```bash
decision-trace ingest generic-jsonl \
  --from-file examples/generic_jsonl_basic_agent/input/agent_log.jsonl \
  --mapping examples/generic_jsonl_basic_agent/input/mapping.yaml \
  --scenario-id generic_jsonl_basic_agent_demo \
  --redact-fields metadata.session_token \
  --out examples/generic_jsonl_basic_agent/expected_output/fragments.json
```
