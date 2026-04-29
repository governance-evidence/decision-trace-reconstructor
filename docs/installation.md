# Installation

Decision Trace Reconstructor uses a small core runtime and optional extras for source-specific adapters.

## Core Package

Install the released package:

```bash
pip install decision-trace-reconstructor
```

Or install from a repository checkout:

```bash
pip install -e .
```

The core package requires Python 3.11+ and `pydantic`.

## Adapter Extras

Install only the adapter extras needed for the source system:

```bash
pip install 'decision-trace-reconstructor[langsmith]'        # LangSmith / LangGraph
pip install 'decision-trace-reconstructor[otlp]'             # OpenTelemetry GenAI OTLP
pip install 'decision-trace-reconstructor[bedrock]'          # AWS Bedrock AgentCore
pip install 'decision-trace-reconstructor[openai-agents]'    # OpenAI Agents SDK
pip install 'decision-trace-reconstructor[anthropic]'        # Anthropic Messages / Computer Use
pip install 'decision-trace-reconstructor[mcp]'              # Model Context Protocol
pip install 'decision-trace-reconstructor[crewai]'           # CrewAI
pip install 'decision-trace-reconstructor[agentframework]'   # Microsoft Agent Framework / AutoGen
pip install 'decision-trace-reconstructor[pydantic-ai]'      # Pydantic AI
```

Generic JSONL ingest has no extra dependency.

From a repository checkout, replace `decision-trace-reconstructor[extra]` with `-e '.[extra]'`.
The CrewAI upstream package currently supports Python versions below 3.14; on Python 3.14,
the exported-telemetry adapter remains available without installing the CrewAI SDK.

## All Adapters

```bash
pip install 'decision-trace-reconstructor[all]'
```

## Development

```bash
make install-dev
```

`make install-dev` installs the editable package with the same development and Parquet extras used by CI.

## Related

- [Adapter documentation](adapters/README.md)
- [Development](development.md)
