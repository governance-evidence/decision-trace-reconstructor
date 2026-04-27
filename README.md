# Decision Trace Reconstructor

**Decision Trace Reconstructor makes agent decisions auditable after the fact: it shows whether the available traces are enough to reconstruct what happened, and names every missing or opaque decision fact.**

Instead of generating another narrative, it produces a **per-property reconstructability matrix**: which decision-event fields are evidenced, partial, structurally absent, or opaque. No synthetic rationale is invented.

## Supported Adapters

Full adapter documentation lives in [`docs/adapters/`](docs/adapters/README.md). Each adapter supports offline file ingest; vendor-backed adapters also support live/network ingest when the optional extra and credentials are available.

| # | Adapter | Extra | Covers |
|---|---|---|---|
| 01 | [`langsmith`](docs/adapters/langsmith.md) | `[langsmith]` | LangChain / LangGraph ecosystem |
| 02 | [`otlp`](docs/adapters/otlp.md) | `[otlp]` | OpenTelemetry GenAI — one adapter, many backends |
| 03 | [`bedrock`](docs/adapters/bedrock.md) | `[bedrock]` | AWS Bedrock AgentCore |
| 04 | [`openai-agents`](docs/adapters/openai-agents.md) | `[openai-agents]` | OpenAI Agents SDK + Traces dashboard exports |
| 05 | [`anthropic`](docs/adapters/anthropic.md) | `[anthropic]` | Anthropic Messages API + Computer Use |
| 06 | [`mcp`](docs/adapters/mcp.md) | `[mcp]` | Model Context Protocol transcripts |
| 07 | [`crewai`](docs/adapters/crewai.md) | `[crewai]` | CrewAI multi-agent telemetry |
| 08 | [`agentframework`](docs/adapters/agentframework.md) | `[agentframework]` | Microsoft Agent Framework / AutoGen v0.4 |
| 09 | [`pydantic-ai`](docs/adapters/pydantic-ai.md) | `[pydantic-ai]` | Pydantic AI run records |
| 10 | [`generic-jsonl`](docs/adapters/generic-jsonl.md) | none | Custom JSONL logs via mapping config |

Unsupported source systems should use [`generic-jsonl`](docs/adapters/generic-jsonl.md) first. If OpenTelemetry GenAI spans are available, [`otlp`](docs/adapters/otlp.md) is usually the better long-term integration path.

## Quick Start

```bash
# 1. Install with the relevant adapter extra
pip install -e '.[langsmith]'   # or [otlp], [bedrock], [openai-agents], ...

# 2. Ingest a trace into a fragments manifest
decision-trace ingest langsmith --from-file traces/agent_run.json \
  --architecture single_agent --stack-tier within_stack \
  --state-mutation-tools "(write|exec|drop|delete|update)" \
  --out fragments.json

# 3. Reconstruct and emit evidence reports
decision-trace reconstruct fragments.json --out report/ --jsonld
```

Output:

- `report/feasibility.json`: per-property reconstructability categories, gap descriptions, and completeness percentage
- `report/trace.jsonld`: W3C PROV-O graph, queryable via SPARQL

Ingest can also be piped directly into reconstruction:

```bash
decision-trace ingest langsmith --from-file traces/run.json --out - | \
  decision-trace reconstruct /dev/stdin --out report/ --jsonld
```

## Result Shape

The report is intentionally diagnostic, not narrative:

| Property | Category | Gap |
|---|---|---|
| `inputs` | `fully_fillable` | none |
| `policy_basis` | `structurally_unfillable` | active policy was not recorded |
| `reasoning_trace` | `opaque` | model reasoning is not externally observable |

## Documentation

- [Installation](docs/installation.md)
- [Adapter documentation](docs/adapters/README.md)
- [Reports and output artifacts](docs/reports.md)
- [Reconstruction architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Roadmap](docs/roadmap.md)

## Examples

Worked examples live under `examples/<adapter>_basic_agent/` and are pinned by integration tests for bit-identical reproduction. The named incident example `examples/replit_drop_database/` shows reconstruction from a public-record fragment manifest.

## Related Work Status

- Companion papers for the Decision Evidence Maturity Model and related evidence-regime concepts are in preparation. They are intentionally not cited as publications until public identifiers exist.
- **Conceptual dependencies:** the Decision Event Schema, the upstream Evidence Collector SDK, and the downstream Governance Benchmark Dataset.

## Citation

`CITATION.cff`, `codemeta.json`, and `ro-crate-metadata.json` ship with the package. The release will be archived on Zenodo with a DOI once tagged.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
