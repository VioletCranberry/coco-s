---
phase: 19-config-env-var-substitution
plan: 01
subsystem: config
tags: [env-vars, yaml, regex, testing, tdd]

# Dependency graph
requires: []
provides:
  - substitute_env_vars function for ${VAR} syntax
  - ${VAR:-default} syntax for defaults
  - Recursive substitution in nested data structures
  - Missing variable collection for error reporting
affects: [19-02]

# Tech tracking
tech-stack:
  added: []
  patterns: [regex-based substitution, recursive data processing]

key-files:
  created:
    - src/cocosearch/config/env_substitution.py
    - tests/unit/config/test_env_substitution.py
  modified: []

key-decisions:
  - "Hand-roll regex substitution (no new dependencies)"
  - "Return tuple (result, missing_vars) for caller to handle errors"
  - "Deduplicate missing vars while preserving order"

patterns-established:
  - "Post-parse substitution: Process YAML after loading, before validation"
  - "re.sub with replacer function for pattern matching"

# Metrics
duration: 2min
completed: 2026-01-31
---

# Phase 19 Plan 01: TDD Env Var Substitution Summary

**Pure function `substitute_env_vars()` with ${VAR} and ${VAR:-default} syntax, 26 passing tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-31T19:38:01Z
- **Completed:** 2026-01-31T19:40:07Z
- **Tasks:** 2 (RED + GREEN, no refactor needed)
- **Files modified:** 2

## Accomplishments

- Created `substitute_env_vars(data) -> tuple[Any, list[str]]` function
- Supports ${VAR} syntax for required environment variables
- Supports ${VAR:-default} syntax for optional vars with fallback
- Recursively processes dicts and lists
- Returns list of missing required env vars for error handling
- 26 comprehensive tests covering all specified behaviors

## Task Commits

TDD plan with RED-GREEN cycle (no refactor needed):

1. **RED: Add failing tests** - `362d28e` (test)
2. **GREEN: Implement substitute_env_vars** - `c721a82` (feat)

## Files Created/Modified

- `src/cocosearch/config/env_substitution.py` - Pure function for env var substitution
- `tests/unit/config/test_env_substitution.py` - 26 unit tests (296 lines)

## Decisions Made

1. **Hand-rolled regex instead of library**: Scope is narrow (string substitution only), keeps implementation transparent, avoids new dependency
2. **Return tuple with missing vars**: Caller (loader.py in 19-02) can decide error handling strategy
3. **Deduplicate missing vars**: Same var referenced multiple times appears once in missing list

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `substitute_env_vars` function ready for integration into loader.py
- Clear API: `(result, missing_vars) = substitute_env_vars(data)`
- Ready for 19-02-PLAN.md: Integration into config loader

---
*Phase: 19-config-env-var-substitution*
*Completed: 2026-01-31*
