# Phase 25: Auto-Detect Feature - Research

**Researched:** 2026-02-02
**Domain:** Project context detection, filesystem path resolution, caching strategies
**Confidence:** HIGH

## Summary

This phase implements automatic project context detection for MCP tools based on working directory. The core challenges involve walking directory trees to find git repositories or config files, resolving symlinks to canonical paths to prevent duplicate indexes, detecting collisions when multiple projects map to the same index name, and providing helpful error messages when auto-detection fails.

The standard approach uses Python's pathlib.Path.resolve() for symlink resolution, subprocess with git rev-parse for git root detection, and functools.lru_cache for caching path-to-index mappings. The detection priority chain (cocosearch.yaml indexName > git repo name > directory name) is already defined in CONTEXT.md and follows established patterns from tools like eslint and prettier.

PostgreSQL will store path-to-index mappings in a new metadata table with TEXT columns for paths (unbounded length, allows for long paths) and appropriate constraints for collision detection. MCP tool responses use the isError flag pattern to communicate missing indexes or collisions to the LLM, enabling it to guide users toward resolution.

**Primary recommendation:** Use pathlib.Path.resolve() with strict=False for symlink resolution, functools.lru_cache for caching with maxsize=128, and PostgreSQL TEXT columns for path storage with unique constraints for collision detection.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib | stdlib (3.11+) | Filesystem path operations with symlink resolution | Built-in, object-oriented, cross-platform path handling |
| subprocess | stdlib (3.11+) | Execute git commands for repo detection | Standard way to invoke external processes securely |
| functools | stdlib (3.11+) | LRU cache decorator for path-to-index mapping | Built-in memoization with thread-safe implementation |
| psycopg | 3.3.2+ | PostgreSQL database adapter | Already in project dependencies, modern async support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich | 13.0.0+ | Console output formatting | Already in project for CLI error messages |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pathlib.Path.resolve() | os.path.realpath() | realpath() is slightly faster but less object-oriented, pathlib preferred for consistency |
| subprocess with git CLI | GitPython library | GitPython adds dependency for simple operation, subprocess sufficient |
| functools.lru_cache | cachetools library | cachetools offers TTL/LFU strategies but stdlib is sufficient for stable mappings |

**Installation:**
All required libraries already in project dependencies (pyproject.toml).

## Architecture Patterns

### Recommended Project Structure
```
src/cocosearch/
├── management/
│   ├── git.py              # Git root detection (exists)
│   ├── discovery.py        # Index listing (exists)
│   └── context.py          # NEW: Auto-detection logic
├── config/
│   ├── loader.py           # Config file discovery (exists)
│   └── schema.py           # indexName field (exists)
└── search/
    └── db.py               # Connection pool (exists)
```

### Pattern 1: Directory Tree Walking for Project Root Detection
**What:** Walk up directory tree from cwd to find .git directory or cocosearch.yaml file
**When to use:** On every MCP tool invocation when index_name parameter is None
**Example:**
```python
# Source: Pattern derived from pathlib docs and project's existing git.py
from pathlib import Path

def find_project_root(start_path: Path | None = None) -> tuple[Path | None, str | None]:
    """Walk up directory tree to find project root.

    Returns:
        Tuple of (root_path, detection_method) or (None, None) if not found.
        detection_method is one of: "git", "config", None
    """
    if start_path is None:
        start_path = Path.cwd()

    # Resolve symlinks to canonical path
    current = start_path.resolve(strict=False)

    # Walk up until we hit filesystem root
    while current != current.parent:
        # Check for .git directory (git repo root)
        if (current / ".git").exists():
            return current, "git"

        # Check for cocosearch.yaml (project with explicit config)
        if (current / "cocosearch.yaml").exists():
            return current, "config"

        # Move to parent directory
        current = current.parent

    # Check root directory itself
    if (current / ".git").exists():
        return current, "git"
    if (current / "cocosearch.yaml").exists():
        return current, "config"

    return None, None
```

### Pattern 2: Symlink Resolution for Duplicate Detection
**What:** Resolve all paths to their canonical form to prevent same directory indexed under multiple names
**When to use:** Before deriving index name or storing path-to-index mappings
**Example:**
```python
# Source: https://docs.python.org/3/library/pathlib.html
from pathlib import Path

def get_canonical_path(path: str | Path) -> Path:
    """Resolve path to canonical form, following symlinks.

    Args:
        path: Path to resolve (may be relative or symlinked)

    Returns:
        Absolute path with all symlinks resolved
    """
    # strict=False allows resolving paths even if they don't exist yet
    # This handles case where we're checking before directory is created
    return Path(path).resolve(strict=False)
```

### Pattern 3: LRU Cache for Path-to-Index Mappings
**What:** Cache path-to-index lookups in memory to avoid repeated database queries
**When to use:** Auto-detection function called on every MCP tool invocation
**Example:**
```python
# Source: https://docs.python.org/3/library/functools.html
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=128)
def get_index_for_path(canonical_path: str) -> str | None:
    """Get index name for a canonical path.

    Args:
        canonical_path: Absolute, symlink-resolved path as string

    Returns:
        Index name if mapping exists, None otherwise

    Note:
        - Uses str not Path because Path objects aren't hashable consistently
        - maxsize=128 sufficient for typical developer workstation (10-20 projects)
        - Thread-safe (functools.lru_cache guarantees this)
        - Call .cache_clear() if database is updated externally
    """
    # Query database for path mapping
    # (Implementation will use psycopg connection pool)
    ...
```

### Pattern 4: MCP Tool Error Response with Helpful Guidance
**What:** Return structured error response with isError=False, treating missing index as expected state that LLM can help resolve
**When to use:** When auto-detected project has no index
**Example:**
```python
# Source: MCP documentation on error handling patterns
def search_code_with_autodetect(query: str, index_name: str | None = None) -> dict:
    """Search code with automatic project detection."""

    if index_name is None:
        # Auto-detect from working directory
        root_path, method = find_project_root()

        if root_path is None:
            # Not in a project - inform user
            return {
                "error": "No project detected",
                "message": (
                    "Not in a git repository or directory with cocosearch.yaml. "
                    "Either:\n"
                    "1. Navigate to your project directory, or\n"
                    "2. Specify index_name parameter explicitly"
                ),
                "results": []
            }

        index_name = get_or_derive_index_name(root_path, method)

        if not index_exists(index_name):
            # Project detected but not indexed - guide user
            config_path = root_path / "cocosearch.yaml"
            index_cmd = f"cocosearch index {root_path}"
            if config_path.exists():
                config = load_config(config_path)
                if config.indexName:
                    index_cmd += f" --name {config.indexName}"

            return {
                "error": "Index not found",
                "message": (
                    f"Project detected at {root_path} but not indexed.\n"
                    f"To index this project, run:\n"
                    f"  {index_cmd}\n"
                    f"Or use the index_codebase MCP tool:\n"
                    f"  index_codebase(path='{root_path}')"
                ),
                "detected_path": str(root_path),
                "suggested_index_name": index_name,
                "results": []
            }

    # Proceed with search...
```

### Pattern 5: Collision Detection via Database Constraints
**What:** Store path-to-index mappings with unique constraint on index_name to detect collisions
**When to use:** During indexing, store canonical path alongside index name
**Example:**
```python
# Source: PostgreSQL best practices for collision detection
# Schema:
"""
CREATE TABLE IF NOT EXISTS cocosearch_index_metadata (
    index_name TEXT PRIMARY KEY,           -- Index name (unique)
    canonical_path TEXT NOT NULL,          -- Absolute, symlink-resolved path
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for reverse lookup (path -> index_name)
CREATE INDEX idx_canonical_path ON cocosearch_index_metadata(canonical_path);
"""

def register_index_path(index_name: str, project_path: str | Path) -> None:
    """Register path-to-index mapping, detecting collisions.

    Raises:
        ValueError: If index_name already mapped to different path (collision)
    """
    canonical = str(get_canonical_path(project_path))

    # Check for collision: same index_name, different path
    existing = get_index_metadata(index_name)
    if existing and existing['canonical_path'] != canonical:
        raise ValueError(
            f"Index name collision detected: '{index_name}'\n"
            f"  Existing path: {existing['canonical_path']}\n"
            f"  New path: {canonical}\n\n"
            f"To resolve:\n"
            f"  1. Set explicit indexName in cocosearch.yaml at {project_path}, or\n"
            f"  2. Use --index-name flag: cocosearch index {project_path} --name <unique-name>"
        )

    # Store or update mapping
    upsert_index_metadata(index_name, canonical)

    # Clear cache since database changed
    get_index_for_path.cache_clear()
```

### Anti-Patterns to Avoid
- **Storing relative paths in database:** Always store canonical (absolute, symlink-resolved) paths to enable consistent lookups
- **Using Path objects as cache keys:** Path objects aren't consistently hashable, convert to str for lru_cache
- **Subprocess with shell=True:** Security risk for command injection, always use list arguments with shell=False
- **VARCHAR with arbitrary limit for paths:** Use TEXT to avoid arbitrary length restrictions and future migrations
- **Raising exceptions for missing indexes in MCP tools:** Return structured error response instead, allows LLM to guide user

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory tree walking | Custom recursive function | pathlib with .parent property | Handles filesystem root, symlinks, edge cases |
| Git repository detection | Parsing .git/config | subprocess with git rev-parse | Handles submodules, worktrees, git directory location |
| Path symlink resolution | Reading os.readlink() manually | pathlib.Path.resolve() | Handles chains of symlinks, relative paths, .. components |
| In-memory caching | Custom dict with manual eviction | functools.lru_cache | Thread-safe, built-in eviction, cache statistics |
| PostgreSQL connection pooling | Manual connection management | psycopg_pool.ConnectionPool | Connection lifecycle, health checks, concurrency |

**Key insight:** Python's standard library provides robust, well-tested implementations for all filesystem and caching operations. These handle edge cases (symlink loops, filesystem root, race conditions) that custom implementations often miss.

## Common Pitfalls

### Pitfall 1: Symlink Loop Handling
**What goes wrong:** Path.resolve() can encounter symlink loops (A -> B -> A), causing infinite recursion in Python < 3.13
**Why it happens:** Filesystem allows creating circular symlinks, older Python versions raised RuntimeError unconditionally
**How to avoid:** Use strict=False parameter (default in modern Python), which resolves as far as possible without raising
**Warning signs:** RuntimeError: Symlink loop from /path/to/link when resolving paths

### Pitfall 2: Not Resolving Symlinks Before Comparison
**What goes wrong:** Same directory indexed under multiple names because symlinked paths don't match
**Why it happens:** /home/user/project and /home/user/projects/link-to-project are the same directory but string comparison fails
**How to avoid:** Always call .resolve() before deriving index names or comparing paths
**Warning signs:** Users report "can't find index" when working through symlinked directories

### Pitfall 3: Using Path Objects as Cache Keys
**What goes wrong:** Cache misses or TypeError when using Path objects with lru_cache
**Why it happens:** Path objects implement __hash__ but equality depends on string representation, platform-specific behavior
**How to avoid:** Convert Path to str before using as cache key: str(path.resolve())
**Warning signs:** Cache statistics show 0% hit rate, or "unhashable type" errors

### Pitfall 4: Forgetting to Clear Cache After Database Updates
**What goes wrong:** Auto-detection returns stale results after indexing or clearing
**Why it happens:** lru_cache persists across function calls, doesn't know about database changes
**How to avoid:** Call function_name.cache_clear() after any database operation that changes path mappings
**Warning signs:** Users report "index not found" immediately after successful indexing

### Pitfall 5: Exposing Internal Paths in MCP Tool Responses
**What goes wrong:** Error messages include filesystem paths that leak information about server structure
**Why it happens:** Directly including path strings in error responses without sanitization
**How to avoid:** Use relative paths or project names in user-facing messages, log full paths only to stderr
**Warning signs:** Security audit flags filesystem path disclosure in API responses

### Pitfall 6: Not Handling Non-Git, Non-Config Directories
**What goes wrong:** Auto-detection returns None for valid projects that don't have .git or cocosearch.yaml yet
**Why it happens:** Detection logic only checks for these two markers
**How to avoid:** Fall back to current directory name derivation when neither marker found (already implemented in cli.py)
**Warning signs:** Users report "no project detected" when in valid project directories

### Pitfall 7: Race Conditions in Metadata Table Updates
**What goes wrong:** Two concurrent index operations for same project create duplicate or inconsistent metadata
**Why it happens:** UPSERT without proper locking or unique constraints
**How to avoid:** Use INSERT ... ON CONFLICT UPDATE with PRIMARY KEY on index_name, rely on PostgreSQL's ACID guarantees
**Warning signs:** Database constraint violations or inconsistent path mappings

## Code Examples

Verified patterns from official sources:

### Secure Git Command Execution
```python
# Source: https://docs.python.org/3/library/subprocess.html
import subprocess
from pathlib import Path

def get_git_root_secure(start_dir: Path | None = None) -> Path | None:
    """Get git repository root using secure subprocess invocation.

    Returns:
        Path to git root, or None if not in a git repository
    """
    cwd = start_dir or Path.cwd()

    try:
        # SECURE: Pass command as list, shell=False (default)
        # SECURE: No user input interpolation into command
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
            timeout=5  # Prevent hanging on broken git repos
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Not in a git repository
        return None
    except subprocess.TimeoutExpired:
        # Git command hung (corrupted repo?)
        return None
```

### Priority Chain for Index Name Resolution
```python
# Source: Project's 25-CONTEXT.md decisions + existing cli.py patterns
from pathlib import Path
from cocosearch.config import load_config, find_config_file

def resolve_index_name_with_priority(
    project_root: Path,
    detection_method: str
) -> str:
    """Resolve index name following priority chain.

    Priority: cocosearch.yaml indexName > git repo name > directory name

    Args:
        project_root: Canonical path to project root
        detection_method: One of "git", "config", or None

    Returns:
        Index name derived following priority rules
    """
    # Priority 1: cocosearch.yaml indexName field
    if detection_method == "config" or (project_root / "cocosearch.yaml").exists():
        config = load_config(project_root / "cocosearch.yaml")
        if config.indexName:
            return config.indexName

    # Priority 2: Git repository directory name
    # (Note: detection_method == "git" means we found .git)
    # Use directory name regardless, as per derive_index_name() pattern

    # Priority 3: Directory name (always available)
    from cocosearch.cli import derive_index_name
    return derive_index_name(str(project_root))
```

### Thread-Safe Cache with Statistics
```python
# Source: https://docs.python.org/3/library/functools.html
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=128)
def cached_path_lookup(canonical_path: str) -> str | None:
    """Look up index name for path with caching.

    Thread-safe: functools.lru_cache uses locks internally.
    Cache size: 128 entries covers typical development workstation.
    """
    # Database query here...
    pass

# Inspect cache effectiveness (useful for testing/debugging)
def print_cache_stats():
    info = cached_path_lookup.cache_info()
    print(f"Cache hits: {info.hits}")
    print(f"Cache misses: {info.misses}")
    print(f"Hit rate: {info.hits / (info.hits + info.misses):.2%}")
    print(f"Current size: {info.currsize}/{info.maxsize}")

# Clear cache after database updates
def after_index_update():
    cached_path_lookup.cache_clear()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| os.path.realpath() | pathlib.Path.resolve() | Python 3.4+ | Object-oriented API, better cross-platform support |
| subprocess.call() | subprocess.run() | Python 3.5+ | Better error handling, timeout support, cleaner API |
| Manual dict caching | functools.lru_cache | Python 3.2+ (improved 3.8+) | Thread-safe, automatic eviction, statistics |
| VARCHAR(255) for paths | TEXT | PostgreSQL 9.1+ | No arbitrary limits, same performance, no migrations needed |
| RuntimeError on symlink loops | OSError in strict mode, success in non-strict | Python 3.13 (2024) | Consistent error handling, allows partial resolution |

**Deprecated/outdated:**
- os.path.* functions: Use pathlib for new code (os.path still works but less ergonomic)
- subprocess.Popen() for simple cases: Use subprocess.run() for cleaner code
- functools.lru_cache with typed=True for path strings: Unnecessary overhead for string keys

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal cache size for lru_cache**
   - What we know: 128 is default, typical workstation has 10-20 projects
   - What's unclear: Should cache size scale with number of indexes? Impact of cache misses vs memory usage?
   - Recommendation: Start with maxsize=128 (default), add cache_info() logging to monitor hit rate in production, adjust if < 80% hit rate

2. **When to invalidate path cache**
   - What we know: Cache must clear after indexing/clearing operations
   - What's unclear: Should cache have TTL? What if external process updates database?
   - Recommendation: Clear cache after any write operation in same process, accept stale cache for external updates (rare), document cache_clear() for manual invalidation if needed

3. **Error message verbosity in MCP responses**
   - What we know: Should guide user toward resolution, LLM can see full error
   - What's unclear: How much detail? Include commands? Full paths or relative?
   - Recommendation: Include actionable commands and relative paths, let LLM summarize for user, log full details to stderr

4. **Handling submodules and git worktrees**
   - What we know: git rev-parse --show-toplevel returns main repo root
   - What's unclear: Should submodules be separate indexes? How to detect submodule vs parent?
   - Recommendation: Treat submodules as separate projects (they have their own .git), use git rev-parse result directly, defer worktree complexity until user requests it

## Sources

### Primary (HIGH confidence)
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - Path.resolve() method, symlink handling
- [Python functools documentation](https://docs.python.org/3/library/functools.html) - lru_cache and cache decorators
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) - Secure command execution
- [PostgreSQL TEXT data type documentation](https://www.postgresql.org/docs/current/datatype-character.html) - Character types comparison

### Secondary (MEDIUM confidence)
- [Real Python: LRU Cache in Python](https://realpython.com/lru-cache-python/) - Caching best practices and patterns
- [MCP Error Handling Documentation](https://apxml.com/courses/getting-started-model-context-protocol/chapter-3-implementing-tools-and-logic/error-handling-reporting) - Tool error response patterns
- [PostgreSQL TEXT vs VARCHAR comparison](https://airbyte.com/data-engineering-resources/postgres-text-vs-varchar) - Data type selection guidance
- [Heroku CLI Style Guide](https://devcenter.heroku.com/articles/cli-style-guide) - Error message UX patterns

### Tertiary (LOW confidence)
- WebSearch: Python directory tree traversal patterns (2026) - Community patterns for walking directories
- WebSearch: Symlink security best practices (2026) - Path traversal vulnerability prevention

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib modules, well-documented, stable APIs
- Architecture: HIGH - Patterns verified from Python docs and existing codebase
- Pitfalls: HIGH - Derived from official documentation version notes and security best practices
- Database schema: MEDIUM - Pattern is standard but specific column names/constraints are recommendations
- Error message wording: MEDIUM - UX patterns from style guides but specific wording is subjective

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days - stable domain, stdlib rarely changes)
