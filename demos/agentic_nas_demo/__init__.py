"""Clean-room Agentic NAS demo for Conv1d-based Transformers."""

from .model import ConvTransformerLM
from .search import SearchResult, run_search
from .search_space import ArchitectureSpec, BlockSpec, MutationAction

__all__ = [
    "ArchitectureSpec",
    "BlockSpec",
    "ConvTransformerLM",
    "MutationAction",
    "SearchResult",
    "run_search",
]
