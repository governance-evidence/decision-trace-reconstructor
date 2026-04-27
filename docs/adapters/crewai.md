# CrewAI Telemetry Adapter

## Source

Offline CrewAI `TelemetryEvent` JSON / JSONL exports.

## Inputs

Offline event files via `--from-file`, with optional crew-name filtering and architecture auto-detection.

## Fragment Mapping

Crew kickoff emits `config_snapshot`; task, delegation, manager, and consensus events become `agent_message`; tool events become `tool_call`; LLM events become opaque `model_generation`; memory queries become `retrieval_result`; custom policy events can emit `policy_snapshot`.

## Minimal Command

```bash
decision-trace ingest crewai --from-file events.jsonl --auto-architecture --out fragments.json
```

## Worked Example

See [../../examples/crewai_basic_agent/](../../examples/crewai_basic_agent/).
