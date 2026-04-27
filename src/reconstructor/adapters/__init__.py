"""Vendor-specific adapters that translate raw governance evidence into the
``Fragment`` input format.

Adapters are *executable* implementations of the regime-mapping specifications
for supported source systems. Each adapter is independently importable and tested
without requiring the others; optional vendor SDKs live behind named ``[]`` extras in
``pyproject.toml`` (e.g. ``pip install -e '.[langsmith]'``).

Currently implemented:

- ``agentframework`` -- Microsoft Agent Framework / AutoGen telemetry exports
- ``anthropic`` -- Anthropic Messages / Computer Use offline traces
- ``crewai`` -- CrewAI telemetry exports
- ``generic_jsonl`` -- Generic JSONL fallback for custom agent logs
- ``langsmith`` -- LangSmith / LangGraph traces
- ``bedrock`` -- AWS Bedrock AgentCore offline traces
- ``mcp`` -- Model Context Protocol transcript exports
- ``openai_agents`` -- OpenAI Agents SDK offline trace exports
- ``otlp`` -- OpenTelemetry GenAI OTLP JSON / JSONL traces
- ``pydantic_ai`` -- Pydantic AI run-record exports
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

__all__ = [
    "agentframework",
    "anthropic",
    "crewai",
    "generic_jsonl",
    "langsmith",
    "bedrock",
    "mcp",
    "openai_agents",
    "otlp",
    "pydantic_ai",
]


def __getattr__(name: str) -> ModuleType:
    """Lazily expose adapter modules listed in ``__all__``.

    This keeps package-level imports stable without eagerly importing every
    optional adapter facade.
    """
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
