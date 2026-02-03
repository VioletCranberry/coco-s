---
phase: 27-hybrid-search-foundation
plan: 02
subsystem: search
tags: [graceful-degradation, backward-compatibility, schema-detection, hybrid-search]

dependency_graph:
  requires:
    - phase: 27-01
      provides: content_text_field
  provides: [hybrid_column_detection, graceful_degradation_v17]
  affects: [27-03, 28-hybrid-search]

tech_stack:
  added: []
  patterns: [proactive_schema_detection, module_level_flags]

key_files:
  created:
    - tests/unit/test_search_query.py
  modified:
    - src/cocosearch/search/db.py
    - src/cocosearch/search/query.py
    - tests/fixtures/db.py
    - tests/unit/search/test_query.py

decisions:
  - id: proactive_column_check
    choice: "Check column existence proactively before first search"
    reason: "Avoids runtime errors; follows established v1.2 degradation pattern"
  - id: autouse_fixture
    choice: "Use autouse fixture in tests/fixtures/db.py for module state reset"
    reason: "Centralizes test isolation; prevents test pollution across all unit tests"

metrics:
  duration: 8m
  completed: 2026-02-03
---

# Phase 27 Plan 02: Graceful Degradation Summary

**One-liner:** Added runtime hybrid column detection with check_column_exists helper, enabling pre-v1.7 indexes to work with vector-only search while logging a one-time upgrade warning.

## What Was Built

### Schema Inspection Helper (db.py)

Added `check_column_exists()` function that queries `information_schema.columns`:

```python
def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table.

    Used for graceful degradation when schema versions differ.
    For example, pre-v1.7 indexes lack content_text column for hybrid search.
    """
    pool = get_connection_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                )
            """, (table_name, column_name))
            result = cur.fetchone()
            return result[0] if result else False
```

### Hybrid Column Detection (query.py)

Added module-level flags and detection logic following the established v1.2 metadata column pattern:

```python
# Module-level flag for hybrid search column availability
_has_content_text_column = True
_hybrid_warning_emitted = False

# In search() function:
if _has_content_text_column and not _hybrid_warning_emitted:
    if not check_column_exists(table_name, "content_text"):
        _has_content_text_column = False
        logger.warning(
            "Index lacks hybrid search columns (content_text). "
            "Run 'cocosearch index' to enable hybrid search."
        )
        _hybrid_warning_emitted = True
```

Key characteristics:
- Proactive detection on first search (not reactive error handling)
- Warning logged only once per session
- Search continues with vector-only mode if column missing
- Prepares for Phase 28 hybrid search implementation

### Unit Tests

Created `tests/unit/test_search_query.py` with 7 tests:

1. `test_check_column_exists_detects_missing_column` - Returns False for missing
2. `test_check_column_exists_detects_existing_column` - Returns True for existing
3. `test_check_column_exists_passes_table_and_column_names` - Validates params
4. `test_hybrid_warning_logged_when_content_text_missing` - Warning triggers
5. `test_hybrid_warning_logged_only_once` - No duplicate warnings
6. `test_no_warning_when_content_text_exists` - Silent when column exists
7. `test_search_continues_when_hybrid_columns_missing` - Graceful degradation

### Test Infrastructure Update

Added autouse fixture in `tests/fixtures/db.py`:

```python
@pytest.fixture(autouse=True)
def reset_search_module_state():
    """Reset search module state and patch check_column_exists."""
    import cocosearch.search.query as query_module
    with patch.object(query_module, "check_column_exists", return_value=True):
        yield
    # Reset all module-level flags after test
    query_module._has_metadata_columns = True
    query_module._metadata_warning_emitted = False
    query_module._has_content_text_column = True
    query_module._hybrid_warning_emitted = False
```

## Verification Results

```
tests/unit/test_search_query.py - 7 passed
tests/unit/ - 630 passed (no regressions)
```

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Proactive schema check | Check before first query | Avoids UndefinedColumn errors during search; cleaner UX |
| Autouse fixture for tests | Centralized in tests/fixtures/db.py | All unit tests automatically get state isolation |
| Warning message content | Mentions "cocosearch index" | Clear upgrade path for users |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added autouse fixture to prevent test failures**
- **Found during:** Task 3
- **Issue:** New check_column_exists call in search() was hitting real DB in existing tests
- **Fix:** Added autouse fixture in tests/fixtures/db.py that patches check_column_exists
- **Files modified:** tests/fixtures/db.py, tests/unit/search/test_query.py
- **Verification:** All 630 unit tests pass
- **Committed in:** 7c02743 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for test suite to pass. No scope creep.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 8c3b382 | feat | Add check_column_exists helper for schema inspection |
| 3b99d73 | feat | Add hybrid column detection to search function |
| 7c02743 | test | Add unit tests for hybrid search graceful degradation |

## Next Phase Readiness

**Ready for 27-03:** Detection infrastructure complete. Plan 03 will add the TSVECTOR column and GIN index, and Plan 28 will implement the actual hybrid search query using both vector similarity and keyword matching.

**Backward compatibility confirmed:** Pre-v1.7 indexes continue to work with vector-only search. Users see a single warning suggesting re-indexing to enable hybrid search.
