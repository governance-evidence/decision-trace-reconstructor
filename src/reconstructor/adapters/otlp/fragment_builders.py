"""Compatibility facade for normalized OTLP GenAI fragment builders."""

from __future__ import annotations

from .misc_fragments import (
    _agent_message_fragment,
    _config_fragment,
    _error_fragment,
    _message_event_fragments,
    _override_fragment,
)
from .model_fragments import _model_generation_fragment
from .tool_fragments import _tool_fragments

__all__ = [
    "_agent_message_fragment",
    "_config_fragment",
    "_error_fragment",
    "_message_event_fragments",
    "_model_generation_fragment",
    "_override_fragment",
    "_tool_fragments",
]
