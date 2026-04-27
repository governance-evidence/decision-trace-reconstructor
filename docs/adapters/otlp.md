# OpenTelemetry GenAI OTLP Adapter

## Source

OpenTelemetry GenAI spans from any backend that can export OTLP JSON, JSONL, protobuf, or HTTP responses.

## Inputs

Offline files via `--from-file`, OTLP protobuf via `--from-otel-protobuf`, or collector-style HTTP endpoints via `--from-otlp-collector`.

## Fragment Mapping

Normalizes `gen_ai.*` and legacy `llm.*` attributes. Model spans become `model_generation`, tool spans become `tool_call`, user/assistant/system events become `agent_message`, and client spans can be elevated to `cross_stack` when `server.address` falls outside the declared service mesh.

## Minimal Command

```bash
decision-trace ingest otlp --from-file spans.jsonl --out fragments.json
```

## Worked Example

See [../../examples/otlp_basic_agent/](../../examples/otlp_basic_agent/).
