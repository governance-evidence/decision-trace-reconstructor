"""Adapter manifest contract and golden-output tests.

Each public adapter should have one small worked example under ``examples/``
with a checked-in ``expected_output/fragments.json``. These tests are the
shared contract for that boundary: adapters must produce deterministic manifests
that match their golden file and round-trip through the typed wire model.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import reconstructor.adapters as adapters
from reconstructor.core.fragment import StackTier
from reconstructor.core.manifest import FragmentManifest

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples"


@dataclass(frozen=True)
class AdapterContractCase:
    adapter_name: str
    example_name: str
    scenario_id: str
    build_manifest: Callable[[Path, str], dict[str, Any]]

    @property
    def example_dir(self) -> Path:
        return EXAMPLES_DIR / self.example_name

    @property
    def golden_manifest_path(self) -> Path:
        return self.example_dir / "expected_output" / "fragments.json"


def _agentframework_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.agentframework import (
        AgentFrameworkIngestOptions,
        events_to_manifest,
        load_events_file,
    )

    events = load_events_file(example_dir / "input" / "events.jsonl")
    return events_to_manifest(
        events,
        scenario_id=scenario_id,
        opts=AgentFrameworkIngestOptions(
            auto_architecture=True,
            cross_stack_tools_pattern=r"web_search",
            state_mutation_tool_pattern=r"write_.*",
        ),
    )


def _anthropic_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.anthropic import (
        AnthropicIngestOptions,
        load_rounds_file,
        rounds_to_manifest,
    )

    rounds = load_rounds_file(example_dir / "input" / "messages_history.jsonl")
    return rounds_to_manifest(
        rounds,
        scenario_id=scenario_id,
        opts=AnthropicIngestOptions(
            architecture="single_agent",
            stack_tier=StackTier.WITHIN_STACK,
        ),
    )


def _bedrock_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.bedrock import (
        BedrockIngestOptions,
        load_sessions_file,
        sessions_to_manifest,
    )

    sessions = load_sessions_file(example_dir / "input" / "sessions.json")
    return sessions_to_manifest(
        sessions,
        scenario_id=scenario_id,
        opts=BedrockIngestOptions(
            architecture="single_agent",
            stack_tier=StackTier.WITHIN_STACK,
        ),
    )


def _crewai_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.crewai import (
        CrewAIIngestOptions,
        events_to_manifest,
        load_events_file,
    )

    events = load_events_file(example_dir / "input" / "events.jsonl")
    return events_to_manifest(
        events,
        scenario_id=scenario_id,
        opts=CrewAIIngestOptions(
            auto_architecture=True,
            cross_stack_tools_pattern=r"web_search",
            state_mutation_tool_pattern=r"write_.*",
        ),
    )


def _generic_jsonl_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.generic_jsonl import (
        GenericJsonlIngestOptions,
        iter_records_file,
        load_mapping_file,
        records_to_manifest,
    )

    mapping = load_mapping_file(example_dir / "input" / "mapping.yaml")
    records = iter_records_file(example_dir / "input" / "agent_log.jsonl")
    return records_to_manifest(
        records,
        mapping,
        scenario_id=scenario_id,
        opts=GenericJsonlIngestOptions(redact_fields=("metadata.session_token",)),
    )


def _langsmith_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.langsmith import LangSmithIngestOptions, runs_to_manifest

    runs = json.loads((example_dir / "input" / "runs.json").read_text())["runs"]
    return runs_to_manifest(
        runs,
        scenario_id=scenario_id,
        opts=LangSmithIngestOptions(
            architecture="human_in_the_loop",
            stack_tier=StackTier.WITHIN_STACK,
            state_mutation_tool_pattern=r"(archive|drop|delete|exec|push|publish)",
        ),
    )


def _mcp_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.mcp import (
        McpIngestOptions,
        load_transcript_file,
        transcript_to_manifest,
    )

    frames = load_transcript_file(example_dir / "input" / "transcript.jsonl")
    return transcript_to_manifest(
        frames,
        scenario_id=scenario_id,
        opts=McpIngestOptions(
            architecture="single_agent",
            emit_tools_list=True,
            state_mutation_tool_pattern=r"git_commit",
        ),
    )


def _openai_agents_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.openai_agents import (
        OpenAIAgentsIngestOptions,
        load_traces_file,
        trace_to_manifest,
    )

    traces = load_traces_file(example_dir / "input" / "trace.json")
    return trace_to_manifest(
        traces[0],
        scenario_id=scenario_id,
        opts=OpenAIAgentsIngestOptions(
            architecture="single_agent",
            stack_tier=StackTier.WITHIN_STACK,
            state_mutation_tool_pattern=r"write_.*",
            auto_architecture=True,
        ),
    )


def _otlp_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.otlp import OtlpIngestOptions, load_spans_file, spans_to_manifest

    spans = load_spans_file(example_dir / "input" / "spans.json")
    return spans_to_manifest(
        spans,
        scenario_id=scenario_id,
        opts=OtlpIngestOptions(
            architecture="single_agent",
            stack_tier=StackTier.WITHIN_STACK,
            within_stack_services=("agent-api", "internal-rag", "internal-crm"),
            state_mutation_tool_pattern=r"(update|write|delete|drop|exec)",
        ),
    )


def _pydantic_ai_manifest(example_dir: Path, scenario_id: str) -> dict[str, Any]:
    from reconstructor.adapters.pydantic_ai import (
        PydanticAIIngestOptions,
        load_runs_file,
        runs_to_manifest,
    )

    runs = load_runs_file(example_dir / "input" / "runs.jsonl")
    return runs_to_manifest(
        runs,
        scenario_id=scenario_id,
        opts=PydanticAIIngestOptions(
            cross_stack_tools_pattern=r"search_.*",
            takeover_tool_pattern=r"request_.*",
            human_approval_pattern=r"APPROVED",
        ),
    )


ADAPTER_CONTRACTS: tuple[AdapterContractCase, ...] = (
    AdapterContractCase(
        adapter_name="agentframework",
        example_name="agentframework_basic_agent",
        scenario_id="agentframework_basic_agent_demo",
        build_manifest=_agentframework_manifest,
    ),
    AdapterContractCase(
        adapter_name="anthropic",
        example_name="anthropic_basic_agent",
        scenario_id="anthropic_basic_agent_demo",
        build_manifest=_anthropic_manifest,
    ),
    AdapterContractCase(
        adapter_name="bedrock",
        example_name="bedrock_basic_agent",
        scenario_id="bedrock_basic_agent_demo",
        build_manifest=_bedrock_manifest,
    ),
    AdapterContractCase(
        adapter_name="crewai",
        example_name="crewai_basic_agent",
        scenario_id="crewai_basic_agent_demo",
        build_manifest=_crewai_manifest,
    ),
    AdapterContractCase(
        adapter_name="generic_jsonl",
        example_name="generic_jsonl_basic_agent",
        scenario_id="generic_jsonl_basic_agent_demo",
        build_manifest=_generic_jsonl_manifest,
    ),
    AdapterContractCase(
        adapter_name="langsmith",
        example_name="langsmith_basic_agent",
        scenario_id="langsmith_basic_agent_demo",
        build_manifest=_langsmith_manifest,
    ),
    AdapterContractCase(
        adapter_name="mcp",
        example_name="mcp_basic_agent",
        scenario_id="mcp_basic_agent_demo",
        build_manifest=_mcp_manifest,
    ),
    AdapterContractCase(
        adapter_name="openai_agents",
        example_name="openai_agents_basic_agent",
        scenario_id="openai_agents_basic_agent_demo",
        build_manifest=_openai_agents_manifest,
    ),
    AdapterContractCase(
        adapter_name="otlp",
        example_name="otlp_basic_agent",
        scenario_id="otlp_basic_agent_demo",
        build_manifest=_otlp_manifest,
    ),
    AdapterContractCase(
        adapter_name="pydantic_ai",
        example_name="pydantic_ai_basic_agent",
        scenario_id="pydantic_ai_basic_agent_demo",
        build_manifest=_pydantic_ai_manifest,
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _case_id(case: AdapterContractCase) -> str:
    return case.adapter_name


def test_every_public_adapter_has_a_golden_contract() -> None:
    contract_adapters = {case.adapter_name for case in ADAPTER_CONTRACTS}
    assert contract_adapters == set(adapters.__all__)


@pytest.mark.parametrize("case", ADAPTER_CONTRACTS, ids=_case_id)
def test_adapter_manifest_matches_golden_output(case: AdapterContractCase) -> None:
    manifest = case.build_manifest(case.example_dir, case.scenario_id)
    expected = _load_json(case.golden_manifest_path)

    assert manifest == expected


@pytest.mark.parametrize("case", ADAPTER_CONTRACTS, ids=_case_id)
def test_adapter_manifest_generation_is_deterministic(case: AdapterContractCase) -> None:
    first = case.build_manifest(case.example_dir, case.scenario_id)
    second = case.build_manifest(case.example_dir, case.scenario_id)

    assert second == first


@pytest.mark.parametrize("case", ADAPTER_CONTRACTS, ids=_case_id)
def test_adapter_golden_manifest_satisfies_wire_contract(case: AdapterContractCase) -> None:
    golden = _load_json(case.golden_manifest_path)
    manifest = FragmentManifest.from_dict(golden)

    assert set(golden) == {"scenario_id", "architecture", "stack_tier", "fragments"}
    assert manifest.scenario_id == case.scenario_id
    assert manifest.fragments
    assert manifest.to_dict() == golden

    fragment_ids = [fragment.fragment_id for fragment in manifest.fragments]
    assert len(fragment_ids) == len(set(fragment_ids))
    assert all(fragment_id.strip() for fragment_id in fragment_ids)
    assert all(fragment.actor_id.strip() for fragment in manifest.fragments)
    assert all(math.isfinite(fragment.timestamp) for fragment in manifest.fragments)
    assert [fragment.timestamp for fragment in manifest.fragments] == sorted(
        fragment.timestamp for fragment in manifest.fragments
    )


@pytest.mark.parametrize("case", ADAPTER_CONTRACTS, ids=_case_id)
def test_adapter_golden_manifest_uses_canonical_json(case: AdapterContractCase) -> None:
    golden = _load_json(case.golden_manifest_path)

    assert case.golden_manifest_path.read_text() == json.dumps(golden, indent=2) + "\n"
