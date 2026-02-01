---
phase: 21-language-chunking-refactor
plan: 02
subsystem: indexer
tags: [hcl, terraform, dockerfile, bash, cocoindex, metadata-extraction, language-handlers]

# Dependency graph
requires:
  - phase: 21-01
    provides: handlers package with Protocol-based plugin architecture
provides:
  - HCL/Terraform handler with .tf/.hcl/.tfvars support
  - Dockerfile handler with build stage metadata extraction
  - Bash/Shell handler with function name detection
  - Autodiscovery registry populated with 3 language handlers
affects: [21-03, 21-04, future-language-handlers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Handler migration pattern: SEPARATOR_SPEC + extract_metadata() in single module"
    - "Comment stripping via _strip_comments() helper for clean metadata extraction"

key-files:
  created:
    - src/cocosearch/handlers/hcl.py
    - src/cocosearch/handlers/dockerfile.py
    - src/cocosearch/handlers/bash.py
  modified:
    - src/cocosearch/handlers/__init__.py

key-decisions:
  - "EXTENSIONS use dot format ['.tf', '.hcl'] to match registry lookup expectations"
  - "Each handler includes _strip_comments() helper instead of shared utility to keep modules self-contained"

patterns-established:
  - "Handler migration: Copy SEPARATOR_SPEC from languages.py, extract_metadata from metadata.py, combine in single module"
  - "Metadata dict format: {block_type, hierarchy, language_id} matching existing DevOpsMetadata dataclass structure"

# Metrics
duration: 3min
completed: 2026-02-01
---

# Phase 21 Plan 02: Language Handler Migration Summary

**Self-contained HCL, Dockerfile, and Bash handlers with SEPARATOR_SPEC and metadata extraction migrated from languages.py/metadata.py**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-01T03:44:33Z
- **Completed:** 2026-02-01T03:47:47Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Migrated HCL language definition (12 keywords) and metadata extraction (block/hierarchy) into hcl.py
- Migrated Dockerfile language definition (FROM/instruction separators) and stage name extraction into dockerfile.py
- Migrated Bash language definition (function keywords) and function name extraction into bash.py
- All three handlers auto-register via package import and work with get_handler() lookup

## Task Commits

Each task was committed atomically:

1. **Task 1: Create HCL handler module** - `2e4e577` (feat)
2. **Task 2: Create Dockerfile and Bash handler modules** - `806aa3c` (feat)

**Bug fix:** `e4b8b55` (fix: deduplicate handlers in get_custom_languages)

## Files Created/Modified
- `src/cocosearch/handlers/hcl.py` - HCL/Terraform handler with 12 top-level keywords, extracts resource/data/variable blocks
- `src/cocosearch/handlers/dockerfile.py` - Dockerfile handler with FROM stage detection, extracts build stage names or image refs
- `src/cocosearch/handlers/bash.py` - Bash/Shell handler with function keyword detection, supports 3 function syntaxes (POSIX/ksh/hybrid)
- `src/cocosearch/handlers/__init__.py` - Fixed get_custom_languages() to deduplicate handlers

## Decisions Made

**EXTENSIONS format:** Use dot-prefixed format (['.tf', '.hcl', '.tfvars']) to match get_handler() expectations and registry lookup by extension string.

**Self-contained modules:** Each handler includes its own _strip_comments() helper instead of importing from shared utility. Keeps modules independent and reduces coupling.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed duplicate SEPARATOR_SPECs in get_custom_languages()**
- **Found during:** Overall verification after Task 2
- **Issue:** get_custom_languages() iterated over _HANDLER_REGISTRY.values() which maps extensions to handlers. Since HclHandler registers 3 extensions (.tf/.hcl/.tfvars), the same SEPARATOR_SPEC appeared 3 times. Returned 7 specs instead of 3 unique ones.
- **Fix:** Track seen handlers by id() to return unique SEPARATOR_SPECs only. Added seen_handlers set to deduplicate by object identity.
- **Files modified:** src/cocosearch/handlers/__init__.py
- **Verification:** get_custom_languages() now returns 3 languages (hcl, bash, dockerfile) with no duplicates
- **Committed in:** e4b8b55 (separate bug fix commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Bug fix necessary for correct CocoIndex language registration. No scope creep.

## Issues Encountered
None - all handlers migrated cleanly from existing languages.py and metadata.py code.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 21-03:** Handlers package is functional with 3 language handlers auto-registering. Ready to migrate flow.py to use the new handlers package.

**Registry verification:** All 3 handlers register correctly:
- get_handler('.tf') → HclHandler
- get_handler('.dockerfile') → DockerfileHandler
- get_handler('.sh') → BashHandler
- get_custom_languages() → 3 unique CustomLanguageSpecs

**No blockers or concerns.**

---
*Phase: 21-language-chunking-refactor*
*Plan: 02*
*Completed: 2026-02-01*
