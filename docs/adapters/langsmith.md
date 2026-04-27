# LangSmith / LangGraph Adapter

## Source

LangChain / LangGraph traces from LangSmith run trees.

## Inputs

Offline LangSmith JSON exports via `--from-file`, or live fetch by `--trace-id` / `--run-id` when the optional LangSmith dependency and credentials are available.

## Fragment Mapping

Maps `llm` runs to `model_generation`, `tool` runs to `tool_call`, retriever runs to `retrieval_result`, and chain/prompt runs to `agent_message`. Human approval/rejection can be inferred from LangGraph node metadata, and `policy_snapshot` / `config_snapshot` tags opt in to explicit governance fragments.

## Minimal Command

```bash
decision-trace ingest langsmith --from-file traces/run_export.json --architecture human_in_the_loop --stack-tier within_stack --out fragments.json
```

## Worked Example

See [../../examples/langsmith_basic_agent/](../../examples/langsmith_basic_agent/).
