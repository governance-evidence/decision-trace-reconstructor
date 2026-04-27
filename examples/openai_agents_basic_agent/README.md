# OpenAI Agents basic example

This example captures an offline OpenAI Agents SDK trace export for a two-agent customer-support workflow:

- `triage_agent` performs an input guardrail check and a policy web search
- control hands off to `billing_agent`
- `billing_agent` performs a refund write action and a computer-use click

Generate the pinned manifest with:

```bash
decision-trace ingest openai-agents \
  --from-file examples/openai_agents_basic_agent/input/trace.json \
  --scenario-id openai_agents_basic_agent_demo \
  --auto-architecture \
  --state-mutation-tools 'write_.*' \
  --out examples/openai_agents_basic_agent/expected_output/fragments.json
```
