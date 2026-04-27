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
