# AWS Bedrock AgentCore Adapter

## Source

AWS Bedrock AgentCore session traces and CloudWatch event exports.

## Inputs

Offline JSON / JSONL session exports via `--from-file`, or live CloudWatch fetch via `--log-group` with optional AWS profile, region, session, and time-window filters.

## Fragment Mapping

Emits session-level `config_snapshot` fragments, maps knowledge-base lookups to `retrieval_result`, action-group and code-interpreter calls to `tool_call`, mutating actions to paired `state_mutation`, guardrails to `policy_snapshot`, return-control outcomes to human approval/rejection, and failure traces to `error`.

## Minimal Command

```bash
decision-trace ingest bedrock --from-file cloudwatch_export.jsonl --out fragments.json
```

## Worked Example

See [../../examples/bedrock_basic_agent/](../../examples/bedrock_basic_agent/).
