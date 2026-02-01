---
phase: 21-language-chunking-refactor
plan: 03
subsystem: indexer
tags: [cocoindex, handlers, backward-compatibility, refactor]

# Dependency graph
requires:
  - phase: 21-02
    provides: Handler package with registry-based autodiscovery
provides:
  - flow.py using handlers package for custom languages and metadata
  - Backward-compatible re-exports in languages.py and metadata.py
  - Existing tests continue to work without modification
affects: [phase-22]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backward-compatible re-exports for API migration"
    - "Import from handlers package instead of indexer modules"

key-files:
  created: []
  modified:
    - src/cocosearch/indexer/flow.py
    - src/cocosearch/indexer/languages.py
    - src/cocosearch/indexer/metadata.py

key-decisions:
  - "languages.py re-exports DEVOPS_CUSTOM_LANGUAGES via get_custom_languages() call"
  - "metadata.py re-exports extract_devops_metadata from handlers (avoids double registration)"
  - "Internal patterns (_HCL_COMMENT_LINE, etc.) re-exported for test compatibility"

patterns-established:
  - "Backward-compatible re-exports: keep old API working while using new implementation"
  - "Handler class attributes accessed directly (HclHandler.SEPARATOR_SPEC)"

# Metrics
duration: 2min
completed: 2026-02-01
---

# Phase 21 Plan 03: Flow Integration Summary

**flow.py uses registry-based handlers via get_custom_languages(), backward-compatible re-exports preserve existing API**

## Performance

- **Duration:** 2 minutes
- **Started:** 2026-02-01T03:50:25Z
- **Completed:** 2026-02-01T03:52:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- flow.py imports from handlers package instead of indexer modules
- get_custom_languages() provides dynamic handler discovery
- languages.py re-exports for backward compatibility
- metadata.py re-exports for backward compatibility
- All 74 existing tests pass without modification

## Task Commits

Each task was committed atomically:

1. **Task 1: Update flow.py to use handlers package** - `4540959` (refactor)
2. **Task 2: Create backward-compatible re-exports in old modules** - `eb45909` (refactor)

## Files Created/Modified
- `src/cocosearch/indexer/flow.py` - Imports get_custom_languages() and extract_devops_metadata from handlers
- `src/cocosearch/indexer/languages.py` - Re-exports DEVOPS_CUSTOM_LANGUAGES and individual specs from handlers
- `src/cocosearch/indexer/metadata.py` - Re-exports extract_devops_metadata and internal patterns from handlers

## Decisions Made

**1. Use get_custom_languages() call instead of static list**
- Rationale: Enables dynamic handler discovery, future handlers auto-register

**2. Avoid double registration of extract_devops_metadata**
- Rationale: Old metadata.py had @cocoindex.op.function() decorator, caused RuntimeError
- Solution: Re-export the decorated function from handlers, don't re-decorate

**3. Re-export internal patterns for test compatibility**
- Rationale: Tests import _HCL_COMMENT_LINE, _LANGUAGE_DISPATCH, etc.
- Solution: Map to handler class attributes (HclHandler._COMMENT_LINE, etc.)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Double registration error during initial verification**
- Problem: metadata.py and handlers/__init__.py both decorated extract_devops_metadata
- Solution: Replaced metadata.py implementation with re-export from handlers
- Resolved in Task 2 before committing

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Flow integration complete, indexing uses registry-based handlers
- Backward compatibility verified, all tests pass
- Ready for next phase (cleanup or new features)

---
*Phase: 21-language-chunking-refactor*
*Completed: 2026-02-01*
