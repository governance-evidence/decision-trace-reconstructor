# Pydantic AI Adapter

## Source

Offline Pydantic AI run records captured from `Agent.run()` workflows.

## Inputs

Offline JSON / JSONL run records via `--from-file`.

## Fragment Mapping

Agent metadata and result schema emit `config_snapshot`; user prompts become `agent_message`; model responses become opaque `model_generation`; tool calls become `tool_call`; retry prompts become `error`; takeover tools can emit human approval/rejection fragments.

## Minimal Command

```bash
decision-trace ingest pydantic-ai --from-file runs.jsonl --out fragments.json
```

## Worked Example

See [../../examples/pydantic_ai_basic_agent/](../../examples/pydantic_ai_basic_agent/).
