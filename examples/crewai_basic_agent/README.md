# Worked example: CrewAI telemetry → Decision Trace Reconstructor (`crewai_basic_agent`)

This example exercises the offline CrewAI adapter on a hierarchical crew with three roles in play:

- `Manager` orchestrates the specialist handoff
- `Researcher` uses a cross-stack `web_search` tool
- `Writer` queries long-term memory and uses an in-process `write_markdown` tool

Generate the pinned manifest with:

```bash
decision-trace ingest crewai \
  --from-file examples/crewai_basic_agent/input/events.jsonl \
  --scenario-id crewai_basic_agent_demo \
  --auto-architecture \
  --cross-stack-tools "web_search" \
  --state-mutation-tools "write_.*" \
  --out examples/crewai_basic_agent/expected_output/fragments.json
```
