"""Indexer module for cocosearch."""

from cocosearch.indexer.config import IndexingConfig, load_config
from cocosearch.indexer.file_filter import (
    DEFAULT_EXCLUDES,
    build_exclude_patterns,
    load_gitignore_patterns,
)

__all__ = [
    "DEFAULT_EXCLUDES",
    "IndexingConfig",
    "build_exclude_patterns",
    "load_config",
    "load_gitignore_patterns",
]
