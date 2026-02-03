---
phase: 29-symbol-aware-indexing
plan: 03
subsystem: search
tags: [graceful-degradation, backward-compatibility, schema-detection, symbol-columns]

dependency_graph:
  requires:
    - phase: 29-01
      provides: symbol_extraction_module
  provides: [symbol_column_detection, graceful_degradation_symbols]
  affects: [29-04, future-symbol-filtering]

tech_stack:
  added: []
  patterns: [proactive_schema_detection, module_level_caching]

key_files:
  created: []
  modified:
    - src/cocosearch/search/db.py
    - tests/unit/search/test_db.py

decisions:
  - id: module_level_cache
    choice: "Cache symbol column availability per table in module-level dict"
    reason: "Prevents repeated information_schema queries; follows Phase 27 pattern"
  - id: all_or_nothing
    choice: "Return True only if all three symbol columns exist"
    reason: "Partial schema is invalid; need consistent state for symbol filtering"
  - id: info_logging
    choice: "Log at INFO level when pre-v1.7 index detected"
    reason: "Informational, not an error; helps debugging without alarming users"

metrics:
  duration: 4m
  completed: 2026-02-03
---

# Phase 29 Plan 03: Symbol Column Detection Summary

**One-liner:** Added check_symbol_columns_exist() with module-level caching to detect pre-v1.7 indexes lacking symbol columns, enabling graceful degradation for backward compatibility.

## What Was Built

### Symbol Column Detection (db.py)

Added three functions following the established pattern from Phase 27 hybrid search column detection:

```python
# Module-level cache
_symbol_columns_available: dict[str, bool] = {}

def check_symbol_columns_exist(table_name: str) -> bool:
    """Check if symbol columns exist in a table.

    Uses module-level caching to avoid repeated database queries.
    Pre-v1.7 indexes lack symbol columns; this enables graceful degradation.
    """
    # Check cache first
    if table_name in _symbol_columns_available:
        return _symbol_columns_available[table_name]

    # Query database
    result = _check_all_symbol_columns(table_name)
    _symbol_columns_available[table_name] = result

    if not result:
        logger.info(f"Index {table_name} lacks symbol columns (pre-v1.7)")

    return result

def _check_all_symbol_columns(table_name: str) -> bool:
    """Internal: Check if all three symbol columns exist."""
    required_columns = {"symbol_type", "symbol_name", "symbol_signature"}
    existing = set()

    pool = get_connection_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND column_name = ANY(%s)
            """, (table_name, list(required_columns)))
            existing = {row[0] for row in cur.fetchall()}

    return existing == required_columns

def reset_symbol_columns_cache() -> None:
    """Reset the symbol columns availability cache.

    Used by tests to ensure clean state between test runs.
    """
    global _symbol_columns_available
    _symbol_columns_available = {}
```

Key characteristics:
- Checks for all three symbol columns atomically (symbol_type, symbol_name, symbol_signature)
- Uses module-level cache to avoid repeated database queries
- Returns False for pre-v1.7 indexes (graceful degradation path)
- Logs INFO message once per table when columns missing
- Provides cache reset function for test isolation

### Unit Tests (test_db.py)

Added 5 comprehensive unit tests for symbol column detection:

1. `test_check_symbol_columns_exist_all_present` - Returns True when all three columns exist
2. `test_check_symbol_columns_exist_missing` - Returns False for pre-v1.7 indexes (no columns)
3. `test_check_symbol_columns_exist_partial` - Returns False when only some columns exist
4. `test_check_symbol_columns_exist_cached` - Verifies caching prevents repeated queries
5. `test_reset_symbol_columns_cache` - Verifies cache reset works correctly

All tests use mocked database connections to avoid real database dependencies.

## Verification Results

```
tests/unit/search/test_db.py -k symbol - 5 passed
tests/unit/search/test_db.py - 10 passed (no regressions)
```

Module imports verified successfully.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cache strategy | Module-level dict per table | Prevents repeated queries; same pattern as Phase 27 |
| All-or-nothing | Require all 3 columns | Partial schema invalid; need consistent state |
| Logging level | INFO (not WARNING) | Informational only; pre-v1.7 is expected scenario |
| Test isolation | reset_symbol_columns_cache() | Explicit reset better than autouse fixture for this case |

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 07ecb21 | feat | Add symbol column existence check with caching and tests |

## Next Phase Readiness

**Ready for 29-04:** Symbol column detection infrastructure complete. Future plan can integrate this check into search query logic to gracefully disable symbol filtering when columns are missing.

**Pattern established:** Follows same approach as Phase 27 hybrid search graceful degradation (check_column_exists pattern). Consistent experience across schema version detection.

**Backward compatibility confirmed:** Pre-v1.7 indexes will be detected correctly and can fall back to search without symbol filtering.
