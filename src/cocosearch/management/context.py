"""Context detection module for cocosearch.

Provides functions to detect project root from any subdirectory,
resolve symlinks to canonical paths, and determine the appropriate
index name following the priority chain.
"""

from pathlib import Path


def get_canonical_path(path: str | Path) -> Path:
    """Resolve path to canonical form, following symlinks.

    Args:
        path: Path to resolve (may be relative or symlinked)

    Returns:
        Absolute path with all symlinks resolved
    """
    # strict=False allows resolving paths even if they don't exist yet
    return Path(path).resolve(strict=False)


def find_project_root(start_path: Path | None = None) -> tuple[Path | None, str | None]:
    """Walk up directory tree to find project root.

    Searches for .git directory first (git repository root), then
    cocosearch.yaml (explicit project configuration).

    Args:
        start_path: Directory to start searching from. Defaults to cwd.

    Returns:
        Tuple of (root_path, detection_method) or (None, None) if not found.
        detection_method is one of: "git", "config", or None
    """
    if start_path is None:
        start_path = Path.cwd()

    # Resolve symlinks to canonical path before walking
    current = get_canonical_path(start_path)

    # Walk up until we hit filesystem root
    while True:
        # Check for .git directory (git repo root)
        if (current / ".git").exists():
            return current, "git"

        # Check for cocosearch.yaml (project with explicit config)
        if (current / "cocosearch.yaml").exists():
            return current, "config"

        # Check if we've reached filesystem root
        parent = current.parent
        if parent == current:
            # We're at the root, no project found
            break
        current = parent

    return None, None


def resolve_index_name(project_root: Path, detection_method: str | None) -> str:
    """Resolve index name following priority chain.

    Priority chain:
    1. cocosearch.yaml indexName field (if config exists)
    2. Directory name (derived from project root)

    Args:
        project_root: Canonical path to project root
        detection_method: One of "git", "config", or None

    Returns:
        Index name derived following priority rules
    """
    # Priority 1: cocosearch.yaml indexName field
    config_path = project_root / "cocosearch.yaml"
    if config_path.exists():
        try:
            from cocosearch.config import load_config
            from cocosearch.config.schema import ConfigError

            config = load_config(config_path)
            if config.indexName:
                return config.indexName
        except (ConfigError, Exception):
            # Config invalid or unreadable, fall back to directory name
            pass

    # Priority 2: Directory name (always available)
    # Import at function level to avoid circular imports
    from cocosearch.cli import derive_index_name

    return derive_index_name(str(project_root))
