---
phase: 20-env-var-standardization
plan: 01
subsystem: config
tags: [environment-variables, validation, configuration]

# Dependency graph
requires:
  - phase: 19-config-env-var-substitution
    provides: Config loader with env var substitution support
provides:
  - COCOSEARCH_* environment variable naming standard
  - Environment variable validation module with fail-fast checks
  - Consistent naming across database, embedder, and all tests
affects: [21-forward, config, cli]

# Tech tracking
tech-stack:
  added: []
  patterns: [COCOSEARCH_* prefix for all env vars, fail-fast env validation]

key-files:
  created:
    - src/cocosearch/config/env_validation.py
  modified:
    - src/cocosearch/search/db.py
    - src/cocosearch/indexer/embedder.py
    - tests/unit/search/test_db.py
    - tests/integration/test_e2e_devops.py
    - tests/integration/test_e2e_search.py

key-decisions:
  - "Standardized on COCOSEARCH_* prefix for all environment variables"
  - "COCOSEARCH_OLLAMA_URL is optional (defaults to localhost:11434)"
  - "COCOSEARCH_DATABASE_URL is required and validated"
  - "Added mask_password utility for safe URL display in logs/errors"

patterns-established:
  - "EnvVarError NamedTuple for structured validation errors"
  - "validate_required_env_vars returns list of errors (empty if valid)"
  - "check_env_or_exit uses Rich console for formatted error output"

# Metrics
duration: 3min
completed: 2026-02-01
---

# Phase 20 Plan 01: Core Environment Variable Migration Summary

**Migrated from COCOINDEX_DATABASE_URL and OLLAMA_HOST to standardized COCOSEARCH_DATABASE_URL and COCOSEARCH_OLLAMA_URL with fail-fast validation module**

## Performance

- **Duration:** 3 minutes
- **Started:** 2026-02-01T02:44:58Z
- **Completed:** 2026-02-01T02:47:59Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Standardized environment variable naming across the entire codebase
- Created reusable environment validation module with structured error handling
- Updated all tests (unit and integration) to use new variable names
- Implemented password masking utility for safe credential display

## Task Commits

Each task was committed atomically:

1. **Task 1: Update database module env var and create validation module** - `1401fd4` (feat)
2. **Task 2: Update embedder module env var** - `837f3bb` (feat)
3. **Task 3: Update unit tests** - `b2304ce` (test)

## Files Created/Modified
- `src/cocosearch/config/env_validation.py` - Environment validation with EnvVarError, validate_required_env_vars, check_env_or_exit, mask_password
- `src/cocosearch/search/db.py` - Changed COCOINDEX_DATABASE_URL to COCOSEARCH_DATABASE_URL
- `src/cocosearch/indexer/embedder.py` - Changed OLLAMA_HOST to COCOSEARCH_OLLAMA_URL, renamed variables for clarity
- `tests/unit/search/test_db.py` - Updated assertions for new error messages
- `tests/integration/test_e2e_devops.py` - Updated to use COCOSEARCH_* variables
- `tests/integration/test_e2e_search.py` - Updated to use COCOSEARCH_* variables
- `src/cocosearch/config/__init__.py` - Exported validation functions

## Decisions Made

1. **COCOSEARCH_* prefix for all env vars** - Establishes clear namespace and avoids conflicts with other tools
2. **COCOSEARCH_OLLAMA_URL optional** - Has sensible default (localhost:11434), not required for validation
3. **COCOSEARCH_DATABASE_URL required** - Database connection is essential, must be validated
4. **Structured validation errors** - EnvVarError NamedTuple provides var_name and hint for user-friendly error messages
5. **Password masking utility** - mask_password uses urllib.parse to safely replace passwords with *** in URLs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed integration tests using old env var names**
- **Found during:** Task 1 (Database module update)
- **Issue:** Integration test files test_e2e_devops.py and test_e2e_search.py still used COCOINDEX_DATABASE_URL and OLLAMA_HOST
- **Fix:** Updated all test fixtures to use COCOSEARCH_DATABASE_URL and COCOSEARCH_OLLAMA_URL
- **Files modified:** tests/integration/test_e2e_devops.py, tests/integration/test_e2e_search.py
- **Verification:** Files no longer reference old variable names
- **Committed in:** 1401fd4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix necessary for test correctness. Tests would fail with old variable names after code migration.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

Users will need to update their environment variables:
- Rename `COCOINDEX_DATABASE_URL` → `COCOSEARCH_DATABASE_URL`
- Rename `OLLAMA_HOST` → `COCOSEARCH_OLLAMA_URL`

This will be documented in plan 20-02 (documentation update).

## Next Phase Readiness

Ready for plan 20-02 (documentation updates).

Blockers: None

Concerns: Need to update .env.example and documentation to reflect new variable names.

---
*Phase: 20-env-var-standardization*
*Completed: 2026-02-01*
