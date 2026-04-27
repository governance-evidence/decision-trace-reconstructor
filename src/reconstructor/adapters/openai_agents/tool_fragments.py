"""Compatibility facade for OpenAI Agents tool-family fragment builders."""

from __future__ import annotations

from .computer_fragments import _computer_use_fragments
from .function_fragments import _function_fragments
from .retrieval_fragments import _file_search_fragment, _web_search_fragments

__all__ = [
    "_computer_use_fragments",
    "_file_search_fragment",
    "_function_fragments",
    "_web_search_fragments",
]
