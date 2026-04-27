"""Public facade API contracts.

The implementation is intentionally split into small internal modules. These
tests pin the stable facade exports so future refactors do not silently break
operator-facing imports.
"""

from __future__ import annotations

import importlib

EXPECTED_EXPORTS = {
    "reconstructor.adapters": {
        "agentframework",
        "anthropic",
        "bedrock",
        "crewai",
        "generic_jsonl",
        "langsmith",
        "mcp",
        "openai_agents",
        "otlp",
        "pydantic_ai",
    },
    "reconstructor.adapters.agentframework": {
        "AgentFrameworkIngestOptions",
        "events_to_fragments",
        "events_to_manifest",
        "load_events_file",
        "normalise_agentframework_input",
    },
    "reconstructor.adapters.anthropic": {
        "AnthropicIngestOptions",
        "load_rounds_file",
        "normalise_anthropic_input",
        "rounds_to_fragments",
        "rounds_to_manifest",
    },
    "reconstructor.adapters.bedrock": {
        "BedrockIngestOptions",
        "fetch_agent_memory_contents",
        "fetch_cloudwatch_events",
        "load_sessions_cloudwatch",
        "load_sessions_file",
        "normalise_bedrock_input",
        "sessions_to_fragments",
        "sessions_to_manifest",
        "validate_sessions_complete",
    },
    "reconstructor.adapters.crewai": {
        "CrewAIIngestOptions",
        "events_to_fragments",
        "events_to_manifest",
        "load_events_file",
        "normalise_crewai_input",
    },
    "reconstructor.adapters.generic_jsonl": {
        "FollowupRule",
        "GenericJsonlIngestOptions",
        "GenericJsonlMapping",
        "MappingFields",
        "StateMutationPredicate",
        "iter_jsonl_stream",
        "iter_records_file",
        "load_mapping_file",
        "load_records_file",
        "records_to_fragments",
        "records_to_manifest",
        "validate_mapping_file",
        "validate_mapping_sample",
    },
    "reconstructor.adapters.langsmith": {
        "LangSmithIngestOptions",
        "fetch_run_subtree",
        "fetch_trace",
        "runs_to_fragments",
        "runs_to_manifest",
    },
    "reconstructor.adapters.mcp": {
        "McpIngestOptions",
        "load_transcript_file",
        "normalise_mcp_input",
        "transcript_to_fragments",
        "transcript_to_manifest",
    },
    "reconstructor.adapters.openai_agents": {
        "OpenAIAgentsIngestOptions",
        "load_traces_file",
        "normalise_openai_agents_input",
        "trace_to_fragments",
        "trace_to_manifest",
        "traces_to_manifests",
    },
    "reconstructor.adapters.otlp": {
        "OtlpIngestOptions",
        "load_spans_file",
        "load_spans_protobuf",
        "load_spans_url",
        "normalise_otlp_input",
        "spans_to_fragments",
        "spans_to_manifest",
    },
    "reconstructor.adapters.pydantic_ai": {
        "PydanticAIIngestOptions",
        "load_runs_file",
        "normalise_pydantic_ai_input",
        "runs_to_fragments",
        "runs_to_manifest",
    },
    "reconstructor.mapping.mapper": {
        "map_chain_to_schema",
        "map_chain_to_schema_aggregate",
        "map_unit_to_schema",
        "unrecoverable_mode_for_property",
    },
    "reconstructor.output": {
        "models",
        "prov_jsonld",
    },
    "reconstructor.output.prov_jsonld": {
        "CONTEXT",
        "DEMM_NS",
        "PROV_NS",
        "SCHEMA_NS",
        "cells_to_jsonld",
        "chain_to_jsonld",
        "chains_to_jsonld_bundle",
        "per_scenario_summary_to_jsonld",
    },
}


def test_facade_modules_export_expected_public_names() -> None:
    for module_name, expected_names in EXPECTED_EXPORTS.items():
        module = importlib.import_module(module_name)
        assert set(module.__all__) == expected_names
        for name in expected_names:
            assert hasattr(module, name), f"{module_name}.__all__ includes missing {name!r}"


def test_facade_exports_do_not_include_private_names() -> None:
    for module_name in EXPECTED_EXPORTS:
        module = importlib.import_module(module_name)
        assert all(not name.startswith("_") for name in module.__all__)
