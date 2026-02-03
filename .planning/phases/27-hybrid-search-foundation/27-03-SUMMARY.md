---
phase: 27-hybrid-search-foundation
plan: 03
subsystem: search
tags: [postgresql, tsvector, gin-index, full-text-search, tokenization]

# Dependency graph
requires:
  - phase: 27-01
    provides: content_text field in chunks table
  - phase: 27-02
    provides: graceful degradation for hybrid search columns
provides:
  - tsvector generation module with code-aware tokenization
  - content_tsv_input field in indexing flow
  - schema migration for TSVECTOR column and GIN index
  - verify_hybrid_search_schema for schema validation
affects: [28-hybrid-search-integration, 29-symbol-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generated column pattern: TSVECTOR GENERATED ALWAYS AS (...) STORED"
    - "Idempotent schema migration pattern"
    - "Code identifier tokenization (camelCase, snake_case splitting)"

key-files:
  created:
    - src/cocosearch/indexer/tsvector.py
    - src/cocosearch/indexer/schema_migration.py
    - tests/unit/test_tsvector.py
    - tests/integration/test_hybrid_schema.py
  modified:
    - src/cocosearch/indexer/flow.py

key-decisions:
  - "Use PostgreSQL 'simple' text search config (no stemming for code)"
  - "Split camelCase/snake_case identifiers while preserving originals"
  - "Store preprocessed text in content_tsv_input, generate TSVECTOR as computed column"
  - "GIN index created without CONCURRENTLY for safety"

patterns-established:
  - "Two-phase tsvector: Python preprocessing + PostgreSQL generated column"
  - "Schema migration idempotency via information_schema checks"

# Metrics
duration: 3min
completed: 2026-02-03
---

# Phase 27 Plan 03: tsvector-gin-index Summary

**PostgreSQL tsvector generation with code-aware tokenization (camelCase/snake_case splitting), generated TSVECTOR column, and GIN index for fast keyword search**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-03T06:05:30Z
- **Completed:** 2026-02-03T06:08:46Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- Created tsvector.py module with code-aware identifier splitting (camelCase, snake_case, PascalCase, kebab-case)
- Added content_tsv_input field to indexing flow for preprocessed tsvector text
- Created schema_migration.py with idempotent TSVECTOR column and GIN index creation
- 12 unit tests + 4 integration tests for tsvector generation and schema migration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tsvector generation module** - `f93407a` (feat)
2. **Task 2: Add content_tsv to indexing flow** - `f4f7db2` (feat)
3. **Task 3: Add unit tests for tsvector module** - `821da9e` (test)
4. **Task 4: Create tsvector column and GIN index via SQL migration** - `46e7ca9` (feat)

## Files Created/Modified

- `src/cocosearch/indexer/tsvector.py` - Code-aware tokenization for PostgreSQL to_tsvector
- `src/cocosearch/indexer/schema_migration.py` - Idempotent TSVECTOR column and GIN index creation
- `src/cocosearch/indexer/flow.py` - Added content_tsv_input transform and collection
- `tests/unit/test_tsvector.py` - Unit tests for identifier splitting and preprocessing
- `tests/integration/test_hybrid_schema.py` - Integration tests for schema migration

## Decisions Made

1. **'simple' text search config:** Used PostgreSQL's 'simple' config instead of 'english' because code identifiers shouldn't be stemmed (e.g., "running" should not match "run" in code)

2. **Preserve original identifiers:** Split identifiers (getUserById -> get, User, By, Id) while also preserving the original for exact match searches

3. **Two-phase tsvector generation:** Python preprocessing produces content_tsv_input text, PostgreSQL generated column creates actual TSVECTOR using to_tsvector('simple', ...)

4. **No CONCURRENTLY for GIN index:** Index created without CONCURRENTLY flag to avoid autocommit complexity; intended for maintenance window execution

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TSVECTOR column and GIN index infrastructure complete (HYBR-05, HYBR-06)
- Ready for Phase 28: hybrid search integration (keyword + semantic fusion)
- Re-indexing required to populate content_tsv_input for existing indexes
- Schema migration should be called after CocoIndex creates base table

---
*Phase: 27-hybrid-search-foundation*
*Completed: 2026-02-03*
