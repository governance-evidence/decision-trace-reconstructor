# Changelog

All notable changes to the Decision Trace Reconstructor are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

No changes yet.

## [0.1.0] - 2026-04-28

Initial public release of the Decision Trace Reconstructor: a reproducible toolkit for reconstructing decision traces from agent, orchestration, telemetry, and public-incident evidence.

### Added

- Six-stage reconstruction pipeline: fragment collection, temporal ordering, chain assembly, decision-boundary detection, decision-event schema mapping, and feasibility reporting.
- CLI entry point `decision-trace` with commands for reconstruction, synthetic evaluation, named-incident evaluation, schema export, and adapter-specific ingest flows.
- Ten executable regime adapters: LangSmith/LangGraph, OpenTelemetry GenAI OTLP, AWS Bedrock AgentCore, OpenAI Agents SDK, Anthropic Messages/Computer Use, MCP, CrewAI, Microsoft Agent Framework/AutoGen, Pydantic AI, and Generic JSONL.
- Worked examples and golden-output integration tests for representative agent stacks, plus the `replit_drop_database` public-incident fixture.
- Synthetic scenario generator for the architecture × stack-coverage evaluation matrix and named-incident fixtures.
- Structured output layer with Pydantic v2 models, JSON Schema export, W3C PROV-O JSON-LD, and optional Parquet output.
- Quarto report template rendering evaluation artifacts from `results/*.json`.
- Scientific release metadata and packaging files: `CITATION.cff`, `codemeta.json`, `ro-crate-metadata.json`, `MANIFEST.in`, Apache-2.0 license, and Python 3.11+ package metadata.
- CI and local quality gates for pytest, Ruff, mypy, package build, and metadata validation.

### Changed

- README, report, and release metadata now describe the public artifact set without citing unpublished companion papers.
- Release packaging now includes documentation, examples, results, tests, scripts, and scientific metadata in the source distribution.

### Fixed

- Replaced Python's randomized string `hash()` with a SHA-256-based deterministic seed for reproducible synthetic evaluations across processes, hosts, and Python versions.
- Temporal ordering now respects `parent_trace_id` causality before timestamp tie-breaking, with deterministic fallback for cycles.
- `make check` now includes Ruff format checking, matching the documented local release gate.
