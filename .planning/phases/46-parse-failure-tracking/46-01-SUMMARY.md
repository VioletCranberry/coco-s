---
phase: 46-parse-failure-tracking
plan: 01
subsystem: indexer
tags: [tree-sitter, parse-tracking, postgresql, schema-migration]

# Dependency graph
requires:
  - phase: 43-docker-packaging
    provides: Working indexing pipeline (flow.py, run_index)
  - phase: 31-symbol-extraction
    provides: LANGUAGE_MAP, tree-sitter infrastructure in symbols.py
provides:
  - parse_tracking.py module with detect_parse_status(), track_parse_results(), rebuild_parse_results()
  - ensure_parse_results_table() schema migration
  - Parse tracking integration in run_index() (non-fatal post-indexing step)
  - Parse results table cleanup on clear_index()
affects: [46-02 stats-display, 46-03 test-suite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Post-flow parse detection: tree-sitter parse runs after CocoIndex flow.update(), not during"
    - "Non-fatal tracking: parse tracking failure does not fail indexing"
    - "Rebuild semantics: parse_results table truncated and rebuilt on each index run"

key-files:
  created:
    - src/cocosearch/indexer/parse_tracking.py
  modified:
    - src/cocosearch/indexer/schema_migration.py
    - src/cocosearch/indexer/flow.py
    - src/cocosearch/management/clear.py

key-decisions:
  - "Store tree-sitter language name (e.g. 'python') in parse_results.language, not file extension (e.g. 'py')"
  - "Parse tracking is non-fatal: wrapped in try/except in run_index(), indexing succeeds even if tracking fails"
  - "Individual file read errors recorded as ('error', 'FileNotFoundError: ...') rather than failing entire tracking run"

patterns-established:
  - "Post-flow tracking pattern: query chunks table for DISTINCT filenames, read from disk, process independently"
  - "Non-fatal extension pattern: wrap optional post-processing in try/except with logger.warning"

# Metrics
duration: 2min
completed: 2026-02-08
---

# Phase 46 Plan 01: Parse Tracking Foundation Summary

**Tree-sitter parse status detection module with 4-category classification (ok/partial/error/unsupported), per-index parse_results table, and integration into indexing and clearing pipelines**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-08T17:34:58Z
- **Completed:** 2026-02-08T17:37:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created parse_tracking.py with detect_parse_status() that classifies files using tree-sitter's root_node.has_error
- Added ensure_parse_results_table() to schema_migration.py following existing idempotent migration pattern
- Integrated parse tracking into run_index() as a non-fatal post-indexing step
- Extended clear_index() to drop parse_results table alongside chunks table

## Task Commits

Each task was committed atomically:

1. **Task 1: Create parse_tracking.py module** - `f231880` (feat)
2. **Task 2: Schema migration + flow.py + clear.py integration** - `82b819e` (feat)

## Files Created/Modified
- `src/cocosearch/indexer/parse_tracking.py` - Parse status detection and persistence (detect_parse_status, track_parse_results, rebuild_parse_results, _collect_error_lines)
- `src/cocosearch/indexer/schema_migration.py` - Added ensure_parse_results_table() for per-index parse_results table creation
- `src/cocosearch/indexer/flow.py` - Integrated ensure_parse_results_table() in setup and track_parse_results() after flow.update()
- `src/cocosearch/management/clear.py` - Added DROP TABLE IF EXISTS for cocosearch_parse_results_{index_name}

## Decisions Made
- Store tree-sitter language name (e.g., "python") in parse_results.language column, not the file extension -- this aligns with the display format in stats output
- For unsupported languages, store the language_id value as-is (e.g., "dockerfile") since there is no tree-sitter language name
- Parse tracking is non-fatal: wrapped in try/except so indexing succeeds even if parse tracking fails
- Individual file read errors (e.g., FileNotFoundError) are recorded as status="error" rather than failing the entire tracking run

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Parse tracking data layer is complete and ready for stats aggregation (plan 02)
- cocosearch_parse_results_{index} table created with file_path, language, parse_status, error_message columns
- All downstream plans (stats display, test suite) can build on this foundation

---
*Phase: 46-parse-failure-tracking*
*Completed: 2026-02-08*
