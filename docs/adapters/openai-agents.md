# OpenAI Agents SDK Adapter

## Source

OpenAI Agents SDK trace exports from tracing processors or dashboard downloads.

## Inputs

Offline trace JSON / JSONL via `--from-file`. Multiple traces can be grouped into scenarios with `--group-into-scenarios`.

## Fragment Mapping

Maps response/generation spans to `model_generation`, function spans to `tool_call`, built-in web search and file search to retrieval-oriented fragments, computer-use spans to cross-stack tool/state-mutation fragments, guardrails to `policy_snapshot`, and handoffs to multi-agent actor switching.

## Minimal Command

```bash
decision-trace ingest openai-agents --from-file traces/agent_trace.json --auto-architecture --out fragments.json
```

## Worked Example

See [../../examples/openai_agents_basic_agent/](../../examples/openai_agents_basic_agent/).
