# Phase 11: Test Reorganization - Research

**Researched:** 2026-01-30
**Domain:** pytest test organization, markers, directory structure
**Confidence:** HIGH

## Summary

This research investigates best practices for separating unit and integration tests in pytest. The standard approach uses a two-directory structure (`tests/unit/` and `tests/integration/`) combined with custom markers (`@pytest.mark.unit` and `@pytest.mark.integration`) for flexible test selection.

The key findings are:
- pytest markers must be registered in `pyproject.toml` under `[tool.pytest.ini_options]` to avoid warnings
- The `pytest_collection_modifyitems` hook enables enforcement of marker discipline (warn/fail on unmarked tests)
- Layered `conftest.py` files provide clean fixture organization: shared fixtures at root, test-type-specific fixtures in subdirectories
- Selective test execution uses `-m` flag: `pytest -m unit` or `pytest -m "not integration"`

**Primary recommendation:** Use registered markers with `strict_markers` enabled, implement a `pytest_collection_modifyitems` hook to warn on unmarked tests, and organize fixtures in three conftest.py files (root, unit, integration).

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=9.0.2 | Test framework | Already in use, native marker support |
| pytest-asyncio | >=1.3.0 | Async test support | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-mock | >=3.15.1 | Mocking utilities | Already in use for unit tests |
| pytest-subprocess | >=1.5.3 | Subprocess mocking | Already in use |
| pytest-httpx | >=0.36.0 | HTTP mocking | Already in use |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom markers | Directory-only separation | Markers provide finer-grained control and cross-directory flexibility |
| pytest-unmarked plugin | Custom hook | Plugin not maintained for pytest 8+; custom hook is simple and maintainable |

**No new packages required** - pytest's built-in marker system handles everything needed.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── __init__.py                 # Keep (empty, enables imports)
├── conftest.py                 # SHARED fixtures (reset_db_pool, tmp_codebase)
├── mocks/                      # Keep as-is (shared mock classes)
│   ├── __init__.py
│   ├── db.py                   # MockCursor, MockConnection, MockConnectionPool
│   └── ollama.py               # deterministic_embedding
├── fixtures/                   # Keep as-is (shared fixture definitions)
│   ├── __init__.py
│   ├── db.py                   # mock_db_pool, patched_db_pool
│   ├── ollama.py               # mock_code_to_embedding, embedding_for
│   └── data.py                 # Sample data fixtures
├── unit/                       # NEW: all unit tests
│   ├── __init__.py
│   ├── conftest.py             # Unit-specific fixtures (if any)
│   ├── indexer/                # Mirror src/cocosearch/indexer/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_embedder.py
│   │   ├── test_file_filter.py
│   │   ├── test_flow.py
│   │   ├── test_languages.py
│   │   ├── test_metadata.py
│   │   └── test_progress.py
│   ├── management/             # Mirror src/cocosearch/management/
│   │   ├── __init__.py
│   │   ├── test_clear.py
│   │   ├── test_discovery.py
│   │   ├── test_git.py
│   │   └── test_stats.py
│   ├── mcp/                    # Mirror src/cocosearch/mcp/
│   │   ├── __init__.py
│   │   └── test_server.py
│   ├── search/                 # Mirror src/cocosearch/search/
│   │   ├── __init__.py
│   │   ├── test_db.py
│   │   ├── test_formatter.py
│   │   ├── test_query.py
│   │   └── test_utils.py
│   ├── test_cli.py             # CLI tests
│   ├── test_db_mocks.py        # Mock validation tests
│   ├── test_ollama_mocks.py    # Mock validation tests
│   └── test_setup.py           # Setup tests
└── integration/                # NEW: integration tests (empty initially)
    ├── __init__.py
    └── conftest.py             # Integration fixtures (real DB, Ollama)
```

### Pattern 1: Marker Registration in pyproject.toml
**What:** Register custom markers to avoid warnings and enable strict checking
**When to use:** Always - required for marker-based filtering
**Example:**
```toml
# Source: https://docs.pytest.org/en/stable/how-to/mark.html
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: marks tests as unit tests (use mocks, no infrastructure)",
    "integration: marks tests as integration tests (use real PostgreSQL, Ollama)",
]
```

### Pattern 2: Unmarked Test Warning Hook
**What:** Emit warnings during test collection if tests lack required markers
**When to use:** To enforce marker discipline without breaking existing tests
**Example:**
```python
# Source: https://docs.pytest.org/en/stable/example/markers.html
# tests/conftest.py

import warnings
import pytest

# Built-in markers to ignore when checking for custom markers
BUILTIN_MARKERS = {
    'parametrize', 'skip', 'skipif', 'xfail', 'usefixtures',
    'filterwarnings', 'asyncio'
}

# Required custom markers - tests must have at least one
REQUIRED_MARKERS = {'unit', 'integration'}


def pytest_collection_modifyitems(items):
    """Warn if tests are missing unit/integration markers."""
    for item in items:
        marker_names = {mark.name for mark in item.iter_markers()}
        custom_markers = marker_names - BUILTIN_MARKERS

        if not custom_markers.intersection(REQUIRED_MARKERS):
            warnings.warn(
                f"Test '{item.nodeid}' has no @pytest.mark.unit or "
                f"@pytest.mark.integration marker",
                UserWarning
            )
```

### Pattern 3: Layered conftest.py Organization
**What:** Split fixtures by scope - shared vs test-type-specific
**When to use:** When unit and integration tests need different fixtures

**Root conftest.py (tests/conftest.py):**
```python
# Source: pytest documentation - fixture scoping
"""Root conftest.py - shared fixtures for all tests."""

import pytest

# Register fixture plugins (these provide fixtures for all tests)
pytest_plugins = [
    "tests.fixtures.db",
    "tests.fixtures.ollama",
    "tests.fixtures.data",
]

# Marker enforcement hook
BUILTIN_MARKERS = {'parametrize', 'skip', 'skipif', 'xfail', 'usefixtures', 'filterwarnings', 'asyncio'}
REQUIRED_MARKERS = {'unit', 'integration'}

def pytest_collection_modifyitems(items):
    """Warn if tests are missing unit/integration markers."""
    import warnings
    for item in items:
        marker_names = {mark.name for mark in item.iter_markers()}
        custom_markers = marker_names - BUILTIN_MARKERS
        if not custom_markers.intersection(REQUIRED_MARKERS):
            warnings.warn(
                f"Test '{item.nodeid}' has no @pytest.mark.unit or @pytest.mark.integration marker",
                UserWarning
            )

@pytest.fixture(autouse=True)
def reset_db_pool():
    """Reset database pool singleton between tests."""
    yield
    import cocosearch.search.db as db_module
    db_module._pool = None

@pytest.fixture
def tmp_codebase(tmp_path):
    """Create a temporary codebase directory with sample files."""
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    (codebase / "main.py").write_text("def hello():\n    return 'world'\n")
    (codebase / ".gitignore").write_text("*.pyc\n__pycache__/\n")
    return codebase
```

**Unit conftest.py (tests/unit/conftest.py):**
```python
"""Unit test conftest.py - unit-specific configuration."""

import pytest

# Auto-apply unit marker to all tests in this directory
def pytest_collection_modifyitems(items):
    """Add unit marker to all tests in tests/unit/."""
    for item in items:
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
```

**Integration conftest.py (tests/integration/conftest.py):**
```python
"""Integration test conftest.py - real infrastructure fixtures."""

import pytest

# Auto-apply integration marker to all tests in this directory
def pytest_collection_modifyitems(items):
    """Add integration marker to all tests in tests/integration/."""
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

# Future: Real database fixtures
# @pytest.fixture(scope="session")
# def real_db_connection():
#     """Provide real PostgreSQL connection for integration tests."""
#     pass
```

### Pattern 4: Selective Test Execution
**What:** Run specific test types using markers
**When to use:** Local development (fast feedback) and CI pipelines
**Example:**
```bash
# Run only unit tests (fast feedback)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all tests except integration (equivalent to -m unit when only two markers)
pytest -m "not integration"

# Run all tests (default)
pytest

# Run by directory (alternative approach)
pytest tests/unit/
pytest tests/integration/
```

### Anti-Patterns to Avoid
- **Duplicating fixtures:** Don't copy fixtures into unit/integration conftest.py - share via pytest_plugins
- **Manual marker on every test:** Use directory-based auto-marking in conftest.py hooks instead
- **Mixing test types in one file:** Keep unit and integration tests in separate files
- **Breaking imports:** Ensure `__init__.py` files exist in all test directories

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test filtering | Custom test loader | `pytest -m marker` | Built-in, well-tested, composable |
| Marker enforcement | Pre-commit script | `pytest_collection_modifyitems` hook | Runs during test collection, integrated |
| Fixture sharing | Copy-paste fixtures | `pytest_plugins` list | Automatic discovery, DRY |
| Directory detection | Path parsing | `item.fspath` in hook | Standard pytest API |

**Key insight:** pytest's hook system handles all test organization needs without external plugins or custom infrastructure.

## Common Pitfalls

### Pitfall 1: Forgetting to Register Markers
**What goes wrong:** `PytestUnknownMarkWarning` on every test run
**Why it happens:** Custom markers like `@pytest.mark.unit` must be declared
**How to avoid:** Add `markers = [...]` to `[tool.pytest.ini_options]` in pyproject.toml
**Warning signs:** Yellow warnings in pytest output mentioning "Unknown pytest.mark"

### Pitfall 2: Breaking Imports After Move
**What goes wrong:** `ModuleNotFoundError` when running tests
**Why it happens:** Missing `__init__.py` files or incorrect import paths in tests
**How to avoid:** Create `__init__.py` in every test directory; use absolute imports
**Warning signs:** Tests pass individually but fail when run together

### Pitfall 3: Conftest Hook Ordering
**What goes wrong:** Markers not applied or warnings not raised
**Why it happens:** Multiple `pytest_collection_modifyitems` hooks run in undefined order
**How to avoid:** Put marker enforcement in root conftest.py; auto-marking in subdirectory conftest.py files
**Warning signs:** Some tests have markers, others don't

### Pitfall 4: Stale pytest_plugins Reference
**What goes wrong:** `ModuleNotFoundError: No module named 'tests.fixtures'`
**Why it happens:** `pytest_plugins` paths are module paths, not file paths
**How to avoid:** Verify paths match actual module structure; ensure fixtures/ has `__init__.py`
**Warning signs:** Tests fail immediately before any collection

### Pitfall 5: Strict Markers Breaking Migration
**What goes wrong:** Tests fail collection due to unmarked tests
**Why it happens:** `--strict-markers` treats unmarked tests as errors
**How to avoid:** Use warning hook (not error) during migration; switch to strict after all tests marked
**Warning signs:** Collection errors instead of warnings

### Pitfall 6: Fixture Scope in Integration Tests
**What goes wrong:** Database state bleeds between tests; tests pass individually but fail together
**Why it happens:** Session-scoped fixtures shared incorrectly across tests
**How to avoid:** Use `scope="function"` for mutable state; clean up in fixtures
**Warning signs:** Non-deterministic test failures

## Code Examples

Verified patterns from official sources:

### Registering Markers
```toml
# Source: https://docs.pytest.org/en/stable/how-to/mark.html
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: marks tests as unit tests (use mocks, no infrastructure)",
    "integration: marks tests as integration tests (use real PostgreSQL, Ollama)",
]
```

### Accessing Markers in Hooks
```python
# Source: https://docs.pytest.org/en/stable/example/markers.html
def pytest_collection_modifyitems(items):
    for item in items:
        # Get all marker names on this test
        marker_names = {mark.name for mark in item.iter_markers()}

        # Check for specific marker
        if "unit" in marker_names:
            print(f"Unit test: {item.nodeid}")

        # Add marker dynamically
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
```

### Selective Execution Commands
```bash
# Source: https://docs.pytest.org/en/stable/example/markers.html
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run all except integration (fast feedback)
pytest -m "not integration"

# Combine with other options
pytest -m unit -v --tb=short

# Run specific directory
pytest tests/unit/indexer/
```

### Fixture Plugin Registration
```python
# Source: https://docs.pytest.org/en/stable/how-to/fixtures.html
# tests/conftest.py
pytest_plugins = [
    "tests.fixtures.db",      # Loads tests/fixtures/db.py fixtures
    "tests.fixtures.ollama",  # Loads tests/fixtures/ollama.py fixtures
    "tests.fixtures.data",    # Loads tests/fixtures/data.py fixtures
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Directory-only separation | Markers + directories | pytest 3.0+ | More flexible filtering |
| pytest.ini for config | pyproject.toml | pytest 6.0+ | Single config file |
| [pytest] section | [tool.pytest.ini_options] | pytest 6.0-9.0 | Standardization |
| pytest-unmarked plugin | Custom hook | Plugin unmaintained | Works with pytest 8+ |

**Deprecated/outdated:**
- `pytest-unmarked` plugin: Not compatible with pytest 8+; use custom `pytest_collection_modifyitems` hook instead
- `[pytest]` section in pyproject.toml: Works but `[tool.pytest.ini_options]` is standard

## Open Questions

Things that couldn't be fully resolved:

1. **Auto-marker vs Explicit Marker?**
   - What we know: Can auto-apply markers via conftest.py hooks based on directory
   - What's unclear: Whether auto-marking defeats the purpose of "enforcing discipline"
   - Recommendation: Use auto-marking in conftest.py hooks (simpler migration, less friction), but keep warning hook as safety net

2. **Warning vs Error for Unmarked Tests?**
   - What we know: Warnings allow gradual adoption; errors enforce strict discipline
   - What's unclear: Team preference for strictness level
   - Recommendation: Start with warnings during migration, optionally add error mode via env var or flag for CI

3. **Root-level test files (test_cli.py, etc.)?**
   - What we know: These exist at tests/ root, should move to tests/unit/
   - What's unclear: Whether to keep flat or nest under a module directory
   - Recommendation: Keep flat in tests/unit/ (test_cli.py tests top-level cli.py)

## Sources

### Primary (HIGH confidence)
- [pytest documentation - markers](https://docs.pytest.org/en/stable/how-to/mark.html) - marker registration, strict_markers
- [pytest documentation - custom markers](https://docs.pytest.org/en/stable/example/markers.html) - pytest_collection_modifyitems, iter_markers
- [pytest documentation - configuration](https://docs.pytest.org/en/stable/reference/customize.html) - pyproject.toml format

### Secondary (MEDIUM confidence)
- [pytest-with-eric - organize tests](https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/) - directory structure patterns
- [pythontutorials.net - separate unit integration](https://www.pythontutorials.net/blog/how-to-keep-unit-tests-and-integrations-tests-separate-in-pytest/) - CI/CD patterns

### Tertiary (LOW confidence)
- Web search results about pytest-unmarked plugin status - confirmed unmaintained for pytest 8+

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using existing pytest features, verified in official docs
- Architecture: HIGH - patterns verified in official docs and multiple credible sources
- Pitfalls: HIGH - derived from official docs warnings and common issues

**Research date:** 2026-01-30
**Valid until:** 60 days (pytest is stable, patterns don't change rapidly)
