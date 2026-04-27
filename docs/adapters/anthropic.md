# Anthropic Messages API + Computer Use Adapter

## Source

Captured Anthropic Messages API request/response rounds, including Computer Use, bash, and text-editor tool blocks.

## Inputs

Offline JSON / JSONL round exports via `--from-file`.

## Fragment Mapping

Request configuration becomes `config_snapshot`, text turns become `agent_message`, response summaries become `model_generation`, thinking blocks stay behind the opacity boundary, tool-use blocks become `tool_call`, and Computer Use / bash / text-editor actions can emit cross-stack state mutations.

## Minimal Command

```bash
decision-trace ingest anthropic --from-file traces/messages_history.jsonl --out fragments.json
```

## Worked Example

See [../../examples/anthropic_basic_agent/](../../examples/anthropic_basic_agent/).
