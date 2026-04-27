"""Compatibility facade for Pydantic AI fragment builders."""

from __future__ import annotations

from .fragment_common import _actor_id, _fragment
from .run_fragments import (
    _config_fragment,
    _model_fragment,
    _result_fragment,
)
from .tool_fragments import (
    _state_fragment,
    _takeover_fragment,
    _tool_fragment,
)

__all__ = [
    "_actor_id",
    "_config_fragment",
    "_fragment",
    "_model_fragment",
    "_result_fragment",
    "_state_fragment",
    "_takeover_fragment",
    "_tool_fragment",
]
