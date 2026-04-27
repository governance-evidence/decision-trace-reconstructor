# Microsoft Agent Framework / AutoGen v0.4 Adapter

## Source

Offline Microsoft Agent Framework / AutoGen v0.4 event streams.

## Inputs

Offline JSON / JSONL `MessageRecord` event files via `--from-file`, with topic filtering and runtime overrides.

## Fragment Mapping

Published messages, agent calls, tool calls, model invocations, speaker selection, and termination events become decision fragments. Legacy v0.2 field names are accepted with deprecation warnings, and gRPC runtime signals can elevate messages to cross-stack.

## Minimal Command

```bash
decision-trace ingest agentframework --from-file events.jsonl --auto-architecture --out fragments.json
```

## Worked Example

See [../../examples/agentframework_basic_agent/](../../examples/agentframework_basic_agent/).
