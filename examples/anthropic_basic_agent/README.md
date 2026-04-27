# Worked example: Anthropic Messages / Computer Use → Decision Trace Reconstructor (`anthropic_basic_agent`)

This example exercises the offline Anthropic adapter on a small but realistic Messages API history for a browser-assisted refund workflow.

The captured rounds show a Claude-driven support agent that:

- takes a screenshot of the billing console
- clicks into the refund form
- types a note
- runs a read-only bash check
- persists a confirmation via the text editor

Generate the pinned manifest with:

```bash
decision-trace ingest anthropic \
  --from-file examples/anthropic_basic_agent/input/messages_history.jsonl \
  --scenario-id anthropic_basic_agent_demo \
  --out examples/anthropic_basic_agent/expected_output/fragments.json
```
