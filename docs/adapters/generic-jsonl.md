# Generic JSONL Adapter

## Source

Custom line-delimited JSON logs from in-house or unsupported agent runtimes.

## Inputs

Offline JSONL via `--from-file` or stdin via `--from-stdin`, plus a YAML or JSON mapping config.

## Fragment Mapping

The mapping config declares field paths, raw-kind to fragment-kind mapping, redaction paths, follow-up absorption rules, stack-tier defaults, and regex-based state-mutation detection. This is the supported fallback for unsupported source systems.

## Minimal Command

```bash
decision-trace ingest generic-jsonl --from-file agent.jsonl --mapping mapping.yaml --out fragments.json
```

## Worked Example

See [../../examples/generic_jsonl_basic_agent/](../../examples/generic_jsonl_basic_agent/).

## Minimal Mapping (No Follow-Up Absorption)

For sources where each record is self-contained — no separate `tool_result` records need to be absorbed into a parent `tool_call` — `absorb_followups` can be omitted entirely or declared as the empty mapping `{}`. The Operational Evidence Plane's Decision Trace Reconstructor integration ships such a minimal mapping at [`integrations/decision-trace-reconstructor/mapping.v0.yaml`](https://github.com/agent-runtime-evidence/operational-evidence-plane/blob/main/integrations/decision-trace-reconstructor/mapping.v0.yaml). Its kind map translates seven OEP record kinds (`manifest`, `prompt`, `policy`, `tool`, `state`, `human`, `final`) into DTR fragment kinds without any follow-up absorption. Use that pattern when the source's records do not come in paired call/result shape.

The fuller worked example at [`../../examples/generic_jsonl_basic_agent/`](../../examples/generic_jsonl_basic_agent/) demonstrates `absorb_followups` for `tool_result` pairing into a parent `tool_call`. Use that pattern when the source emits a tool invocation and a downstream tool-result record that should be folded into the same fragment.
