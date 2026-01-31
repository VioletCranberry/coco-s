"""Configuration module for CocoSearch."""

from .errors import format_validation_errors, suggest_field_name
from .generator import CONFIG_TEMPLATE, generate_config
from .loader import find_config_file, load_config
from .schema import (
    CocoSearchConfig,
    ConfigError,
    EmbeddingSection,
    IndexingSection,
    SearchSection,
)

__all__ = [
    "CocoSearchConfig",
    "ConfigError",
    "EmbeddingSection",
    "IndexingSection",
    "SearchSection",
    "find_config_file",
    "load_config",
    "format_validation_errors",
    "suggest_field_name",
    "generate_config",
    "CONFIG_TEMPLATE",
]
