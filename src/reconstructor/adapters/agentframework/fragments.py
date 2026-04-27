"""Compatibility facade for Agent Framework fragment builders."""

from __future__ import annotations

from .fragment_common import (
    _actor_id,
    _agent_scope,
    _attach_round_context,
    _base_stack_tier,
    _fragment,
    _override_kind,
    _tool_stack_tier,
)
from .message_fragments import (
    _agent_fragment,
    _error_fragment,
    _message_fragment,
    _model_fragment,
    _snapshot_fragment,
)
from .tool_fragments import _state_fragment, _tool_fragment

__all__ = [
    "_actor_id",
    "_agent_fragment",
    "_agent_scope",
    "_attach_round_context",
    "_base_stack_tier",
    "_error_fragment",
    "_fragment",
    "_message_fragment",
    "_model_fragment",
    "_override_kind",
    "_snapshot_fragment",
    "_state_fragment",
    "_tool_fragment",
    "_tool_stack_tier",
]
