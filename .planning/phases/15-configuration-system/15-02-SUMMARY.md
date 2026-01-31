---
phase: 15-configuration-system
plan: 02
subsystem: config
tags: [pydantic, validation, error-formatting, difflib, typo-detection]

# Dependency graph
requires:
  - phase: 15-01
    provides: Pydantic config schema with strict validation
provides:
  - User-friendly validation error messages with typo suggestions
  - All-at-once error reporting with field path context
  - Integration with config loader for automatic error formatting
affects: [15-03-init-command, 16-cli-integration]

# Tech tracking
tech-stack:
  added: [difflib (stdlib)]
  patterns: [Fuzzy field name matching, All-errors-at-once validation reporting]

key-files:
  created:
    - src/cocosearch/config/errors.py
    - tests/unit/config/test_errors.py
  modified:
    - src/cocosearch/config/loader.py
    - src/cocosearch/config/__init__.py

key-decisions:
  - "Use difflib.get_close_matches with cutoff=0.6 for typo detection"
  - "Report all validation errors at once, not just first"
  - "Include config file path in error messages for better context"
  - "Section-specific field suggestions (e.g., 'mdel' → 'model' in embedding section)"

patterns-established:
  - "VALID_FIELDS constant maps sections to field lists for typo detection"
  - "format_validation_errors processes all Pydantic errors into user-friendly format"
  - "Error messages show full field paths for nested fields (e.g., indexing.chunkSize)"

# Metrics
duration: 3min
completed: 2026-01-31
---

# Phase 15 Plan 02: Error Formatting with Typo Suggestions Summary

**User-friendly validation errors with "Did you mean X?" suggestions using difflib fuzzy matching and all-at-once error reporting**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-31T10:28:52Z
- **Completed:** 2026-01-31T10:31:29Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Error formatting module with typo suggestions for unknown config fields
- Integration with loader to automatically format all validation errors
- Comprehensive test coverage (15 tests) for error formatting scenarios
- All validation errors reported at once with full field paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Create error formatting module with typo suggestions** - `8302d32` (feat)
2. **Task 2: Integrate error formatting into loader** - `f2a850d` (feat)
3. **Task 3: Unit tests for error formatting** - `c5fba9f` (test)

## Files Created/Modified
- `src/cocosearch/config/errors.py` - Error formatting with VALID_FIELDS constant, suggest_field_name(), and format_validation_errors()
- `src/cocosearch/config/loader.py` - Integrated error formatter into ValidationError handling
- `src/cocosearch/config/__init__.py` - Exported format_validation_errors and suggest_field_name
- `tests/unit/config/test_errors.py` - 15 tests covering typo suggestions, multiple errors, nested paths, and integration

## What Was Built

### Error Formatting Module (errors.py)

**VALID_FIELDS Constant:**
Maps configuration sections to their valid field lists:
- `root`: indexName, indexing, search, embedding
- `indexing`: includePatterns, excludePatterns, languages, chunkSize, chunkOverlap
- `search`: resultLimit, minScore
- `embedding`: model

**suggest_field_name(unknown: str, section: str = "root") -> str | None:**
- Uses `difflib.get_close_matches()` with cutoff=0.6 for fuzzy matching
- Returns closest matching field name or None if no close match
- Section-specific suggestions (e.g., "mdel" → "model" in embedding, None in root)

**format_validation_errors(exc: ValidationError, config_path: Path | None = None) -> str:**
- Processes all Pydantic validation errors at once
- Builds user-friendly error messages with field paths
- Special handling for:
  - **Unknown fields (extra_forbidden):** Suggests corrections when close match exists
  - **Type errors:** Shows expected vs actual type information
  - **Constraint violations:** Shows validation rule that failed
- Includes config file path in header when provided
- Returns multi-line formatted error message

### Loader Integration

Updated `load_config()` in loader.py to:
- Import and call `format_validation_errors()` on ValidationError
- Pass config file path to formatter for better error context
- Raise ConfigError with formatted message instead of raw Pydantic error

### Test Coverage

Created comprehensive test suite with 15 tests covering:

**Typo Suggestion Tests (6 tests):**
- Close matches for all sections (root, indexing, search, embedding)
- No-match scenarios returning None
- Section-specific matching behavior

**Error Formatting Tests (9 tests):**
- Unknown fields with and without suggestions
- Type errors with expected type information
- Multiple errors reported at once (not just first)
- Nested field paths (e.g., indexing.chunkSize)
- Config path inclusion in header
- Constraint violations

All 15 tests pass.

## Example Error Output

**Invalid config:**
```yaml
indxName: test
indexing:
  chunkSze: 100
```

**Error message:**
```
Configuration errors in /path/to/cocosearch.yaml:
  - indexing.chunkSze: Unknown field. Did you mean 'chunkSize'?
  - indxName: Unknown field. Did you mean 'indexName'?
```

## Decisions Made

**1. difflib cutoff of 0.6 for typo detection**
- Balances between finding close matches and avoiding false positives
- Works well for single character typos and minor misspellings

**2. Report all errors at once**
- Better UX than forcing users to fix errors one at a time
- Pydantic already collects all errors, we just format them all

**3. Include config file path in error messages**
- Provides context when multiple config files might exist
- Helps users locate which config file has the problem

**4. Section-specific field suggestions**
- More accurate suggestions by limiting to fields valid in that section
- Prevents confusing cross-section suggestions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully without issues.

## Next Phase Readiness

Error formatting complete and integrated with loader. Ready for:
- **Plan 15-03:** Init command to generate default config (will benefit from error formatting)
- **Phase 16:** CLI integration (will use load_config with automatic error formatting)

**Dependencies satisfied:**
- Plan 15-01 schema and loader provide the validation foundation
- Error formatting enhances the validation with user-friendly messages

**No blockers** for next plan.

---
*Phase: 15-configuration-system*
*Completed: 2026-01-31*
