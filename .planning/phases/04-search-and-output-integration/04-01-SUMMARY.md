---
phase: 04-search-and-output-integration
plan: 01
subsystem: search-query
tags: [search, metadata, language-filter, graceful-degradation, devops]
dependency-graph:
  requires: [phase-3-flow-integration]
  provides: [extended-search-result, devops-language-filter, alias-resolution, graceful-degradation]
  affects: [04-02-output-integration]
tech-stack:
  added: []
  patterns: [graceful-degradation-via-module-flag, alias-resolution-before-validation]
key-files:
  created: []
  modified:
    - src/cocosearch/search/query.py
    - src/cocosearch/cli.py
    - tests/search/test_query.py
    - tests/mcp/test_server.py
decisions:
  - "LANGUAGE_ALIASES resolves terraform->hcl, shell->bash, sh->bash before validation"
  - "ALL_LANGUAGES is LANGUAGE_EXTENSIONS keys + DEVOPS_LANGUAGES keys; alias keys excluded"
  - "Module-level _has_metadata_columns flag + _metadata_warning_emitted for one-time degradation"
  - "DevOps languages filter via language_id = %s; extension-based via filename LIKE %s"
  - "Pre-v1.2 + DevOps filter raises ValueError; extension filter still works on pre-v1.2"
metrics:
  duration: ~6 minutes
  completed: 2026-01-27
---

# Phase 4 Plan 1: Search Query Layer Summary

Extended SearchResult with DevOps metadata fields, added language filtering with alias resolution, implemented graceful degradation for pre-v1.2 indexes, and updated CLI help text.

## What Was Done

### Task 1: Extend SearchResult, SQL queries, language filter with aliases, and graceful degradation
**Commit:** b96cf7a

- Added `block_type`, `hierarchy`, `language_id` fields to `SearchResult` dataclass (default `""`)
- Created `DEVOPS_LANGUAGES` dict mapping canonical names (hcl, dockerfile, bash) to database values
- Created `LANGUAGE_ALIASES` dict mapping terraform->hcl, shell->bash, sh->bash
- Created `ALL_LANGUAGES` set combining LANGUAGE_EXTENSIONS and DEVOPS_LANGUAGES keys
- Added `validate_language_filter()` function: splits on comma, resolves aliases, validates against ALL_LANGUAGES, raises ValueError with suggestions for unknown names
- Rewrote `search()` SQL to include metadata columns (block_type, hierarchy, language_id) in SELECT
- Added try/except catching UndefinedColumn for pre-v1.2 index graceful degradation
- Module-level `_has_metadata_columns` flag skips metadata SQL on subsequent queries after first failure
- One-time `logging.warning()` emitted when metadata columns are missing
- DevOps languages filter via `language_id = %s` condition; extension-based languages still use `filename LIKE %s`
- Pre-v1.2 index + DevOps language filter raises clear ValueError with upgrade message
- Updated CLI `--lang` help text to include DevOps languages and aliases

### Task 2: Add tests for metadata fields, aliases, DevOps language filter, and graceful degradation
**Commit:** fcdb88b

- Added `TestSearchResult.test_metadata_fields_default_empty_strings` and `test_metadata_fields_set`
- Added `TestValidateLanguageFilter` class with 10 tests: single, multi, whitespace, DevOps, terraform/shell/sh aliases, unknown, mixed
- Added `TestDevOpsLanguageFilter` class with 4 tests: hcl/dockerfile language_id SQL, multi-language, terraform alias
- Added `TestGracefulDegradation` class with 4 tests: empty metadata fallback, warning emission, DevOps filter upgrade error, extension filter on pre-v1.2
- Added `reset_metadata_flag` autouse fixture to prevent test pollution between tests
- Updated existing TestSearch mock results from 4-element to 7-element tuples
- Fixed MCP test_server.py mock results for v1.2 row format (Rule 1 bug fix)
- All 317 tests pass (36 in test_query.py)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated MCP test mock results for v1.2 row format**
- **Found during:** Task 2 (running full test suite)
- **Issue:** Three tests in `tests/mcp/test_server.py` used 4-element tuples for mock DB results, but `search()` now expects 7-element tuples when metadata columns are present
- **Fix:** Updated mock results to include 3 additional empty string metadata fields
- **Files modified:** tests/mcp/test_server.py
- **Commit:** fcdb88b

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Aliases resolved before validation | Plan specifies aliases NOT in ALL_LANGUAGES; resolving first means users get alias behavior silently |
| Module-level flag pattern for degradation | Avoids repeated failing SQL queries within a session; one failure sets flag for all subsequent searches |
| Exception type check via class name | `type(e).__name__ == "UndefinedColumn"` works reliably with psycopg error hierarchy |
| "shell" alias maps to DevOps "bash" | Plan overrides CONTEXT.md (which said no aliases); "shell" in LANGUAGE_EXTENSIONS still exists but alias resolution takes priority |

## Verification Results

1. `python -m pytest tests/search/test_query.py -v` -- 36/36 pass
2. SearchResult defaults -- block_type, hierarchy, language_id all `""`
3. Multi-language validation -- `validate_language_filter('hcl,python')` returns `['hcl', 'python']`
4. Alias resolution -- `validate_language_filter('terraform')` returns `['hcl']`
5. Unknown language -- `validate_language_filter('foobar')` raises ValueError with available list
6. CLI help text -- contains `hcl`, `dockerfile`, `bash`, alias documentation
7. Full test suite -- 317/317 pass

## Next Phase Readiness

Plan 04-02 (Output Integration) can proceed. SearchResult now carries metadata fields, and the query layer handles all DevOps language filtering and graceful degradation. The output layer (formatters and MCP) can read `block_type`, `hierarchy`, and `language_id` from SearchResult objects.
