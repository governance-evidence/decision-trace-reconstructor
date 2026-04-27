# Worked example: Pydantic AI run records → Decision Trace Reconstructor (`pydantic_ai_basic_agent`)

This example exercises the offline Pydantic AI adapter on a typed, single-agent workflow with one validation retry and one human-takeover tool:

- `SupportAgent` emits typed run metadata and result schema
- the first model response fails output validation and triggers a retry
- a takeover tool requests explicit human approval before finalising the answer

Generate the pinned manifest with:

```bash
decision-trace ingest pydantic-ai \
  --from-file examples/pydantic_ai_basic_agent/input/runs.jsonl \
  --scenario-id pydantic_ai_basic_agent_demo \
  --cross-stack-tools "search_.*" \
  --takeover-tool-pattern "request_.*" \
  --human-approval-pattern "APPROVED" \
  --out examples/pydantic_ai_basic_agent/expected_output/fragments.json
```
