# Worked example: MCP transcript → Decision Trace Reconstructor (`mcp_basic_agent`)

This example exercises the offline MCP adapter on a small transcript from a host connected to two MCP servers:

- `filesystem` serves a policy document and exposes a read-only file tool
- `git` exposes a destructive commit tool and triggers one host-side sampling request

The transcript demonstrates that MCP is cross-stack by construction: every fragment is emitted with `stack_tier: cross_stack`.

Generate the pinned manifest with:

```bash
decision-trace ingest mcp \
  --from-file examples/mcp_basic_agent/input/transcript.jsonl \
  --scenario-id mcp_basic_agent_demo \
  --emit-tools-list \
  --state-mutation-tools "git_commit" \
  --out examples/mcp_basic_agent/expected_output/fragments.json
```
