# Model Context Protocol Adapter

## Source

MCP JSON-RPC transcript frames captured at the host-protocol boundary.

## Inputs

Offline transcript JSON / JSONL via `--from-file`, or local Claude Desktop MCP log discovery via `--from-claude-desktop`.

## Fragment Mapping

Pairs JSON-RPC requests and responses by id. Initialization and tool-list responses can emit `config_snapshot`; tool calls emit `tool_call`; resource reads emit `retrieval_result`; prompts emit `agent_message`; sampling requests emit partial `model_generation`; resource updates can emit rate-limited `state_mutation`. MCP fragments are treated as cross-stack.

## Minimal Command

```bash
decision-trace ingest mcp --from-file transcripts/mcp_session.jsonl --emit-tools-list --out fragments.json
```

## Worked Example

See [../../examples/mcp_basic_agent/](../../examples/mcp_basic_agent/).
