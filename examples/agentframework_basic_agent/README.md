# Worked example: Agent Framework events → Decision Trace Reconstructor (`agentframework_basic_agent`)

This example exercises the offline Agent Framework adapter on a small GroupChat-style workflow with three roles:

- `planner` publishes the research topic and terminates the run
- `executor` performs a cross-stack `web_search`
- `critic` reviews the draft through a model call

Generate the pinned manifest with:

```bash
decision-trace ingest agentframework \
  --from-file examples/agentframework_basic_agent/input/events.jsonl \
  --scenario-id agentframework_basic_agent_demo \
  --auto-architecture \
  --cross-stack-tools "web_search" \
  --state-mutation-tools "write_.*" \
  --out examples/agentframework_basic_agent/expected_output/fragments.json
```
