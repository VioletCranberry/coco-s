"""Configuration file generator for CocoSearch."""

from pathlib import Path

from .schema import ConfigError

CONFIG_TEMPLATE = """\
# CocoSearch Configuration
# https://github.com/VioletCranberry/cocosearch

# Index name (optional - defaults to directory name)
# indexName: my-project

indexing:
  # File patterns to include (glob patterns)
  # includePatterns:
  #   - "*.py"
  #   - "*.js"
  #   - "*.ts"

  # File patterns to exclude (glob patterns)
  # excludePatterns:
  #   - "*_test.py"
  #   - "*.min.js"

  # Languages to index (empty = all supported languages)
  # languages:
  #   - python
  #   - typescript

  # Chunk settings
  # chunkSize: 1000
  # chunkOverlap: 300

search:
  # Maximum results returned
  # resultLimit: 10

  # Minimum similarity score (0.0 - 1.0)
  # minScore: 0.3

embedding:
  # Ollama model for embeddings
  # model: nomic-embed-text
"""


def generate_config(path: Path) -> None:
    """Generate a CocoSearch configuration file.

    Args:
        path: Path where the config file should be created.

    Raises:
        ConfigError: If the config file already exists.
    """
    if path.exists():
        raise ConfigError(f"Configuration file already exists: {path}")

    path.write_text(CONFIG_TEMPLATE)
