---
phase: 08-custom-language-definitions-and-file-routing
plan: 02
subsystem: indexer
tags: [cocoindex, language-routing, dockerfile, extract-language, flow, custom-languages]

# Dependency graph
requires:
  - phase: 08-01
    provides: CustomLanguageSpec definitions (HCL, Dockerfile, Bash) and DEVOPS_CUSTOM_LANGUAGES list
provides:
  - extract_language function for filename-based and extension-based language routing
  - Flow integration with custom_languages passed to SplitRecursively
  - Dockerfile/Containerfile extensionless file routing
affects:
  - phase-2 metadata extraction (relies on correct language routing for metadata parsers)
  - phase-3 flow integration (custom_languages already wired into SplitRecursively)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Filename-based routing for extensionless files (Dockerfile, Containerfile)"
    - "extract_language as CocoIndex op function replacing extract_extension for language detection"

key-files:
  created: []
  modified:
    - src/cocosearch/indexer/embedder.py
    - src/cocosearch/indexer/flow.py
    - src/cocosearch/indexer/__init__.py
    - tests/indexer/test_embedder.py
    - tests/indexer/test_flow.py

key-decisions:
  - "extract_language uses basename.startswith('Dockerfile') for all variants, exact match for Containerfile"
  - "Field still called 'extension' in flow.py to minimize downstream changes"
  - "chunk_size default kept at 1000 (not changed to 2000 for DevOps) -- user can configure via .cocosearch.yaml"
  - "extract_extension kept unchanged for backward compatibility"

patterns-established:
  - "Filename pattern routing: check basename patterns first, fall back to extension"
  - "CocoIndex op function composition: extract_language -> SplitRecursively(custom_languages=...)"

# Metrics
duration: 2min
completed: 2026-01-27
---

# Phase 08 Plan 02: Language Routing and Flow Integration Summary

**extract_language function routing Dockerfile/Containerfile by filename and custom_languages wired into SplitRecursively for DevOps-aware chunking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-27T14:04:36Z
- **Completed:** 2026-01-27T14:06:53Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created `extract_language` function that routes Dockerfile/Containerfile by filename pattern and all other files by extension
- Wired `DEVOPS_CUSTOM_LANGUAGES` into `SplitRecursively` constructor in `flow.py`
- Replaced `extract_extension` with `extract_language` in flow language detection step
- Added `extract_language` to `__init__.py` exports
- 21 new tests (15 extract_language + 6 flow integration) all passing, 236 total tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create extract_language function and update routing** - `a137717` (feat)
2. **Task 2: Wire custom_languages into flow and update exports** - `d09fb00` (feat)

## Files Created/Modified
- `src/cocosearch/indexer/embedder.py` - Added extract_language function with filename-based and extension-based routing
- `src/cocosearch/indexer/flow.py` - Imports DEVOPS_CUSTOM_LANGUAGES, passes to SplitRecursively, uses extract_language
- `src/cocosearch/indexer/__init__.py` - Exports extract_language in import and __all__
- `tests/indexer/test_embedder.py` - 15 new tests in TestExtractLanguage class
- `tests/indexer/test_flow.py` - 6 new tests in TestCustomLanguageIntegration class

## Decisions Made
- `extract_language` uses `basename.startswith("Dockerfile")` to catch all variants (Dockerfile, Dockerfile.dev, Dockerfile.production) -- simpler than regex, handles all known patterns
- Exact match for `Containerfile` (not startsWith) to avoid false positives on hypothetical files like "ContainerfileProcessor"
- Flow field kept as `file["extension"]` rather than renaming to `file["language"]` -- minimizes changes to SplitRecursively call site
- chunk_size default left at 1000 -- changing to 2000 for DevOps would affect all files; user can configure via `.cocosearch.yaml`
- `extract_extension` kept intact alongside `extract_language` for backward compatibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 08 (Custom Language Definitions and File Routing) is now COMPLETE
- DevOps files are detected, routed to correct language spec, and chunked at structural boundaries
- Ready for Phase 2 (Metadata Extraction) which adds resource/function name extraction from chunks
- Bare filename pattern validation for Dockerfile/Containerfile in CocoIndex include_patterns remains a LOW-confidence item to validate at integration test time

---
*Phase: 08-custom-language-definitions-and-file-routing*
*Completed: 2026-01-27*
