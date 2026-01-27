---
phase: 08-custom-language-definitions-and-file-routing
plan: 01
subsystem: indexer
tags: [cocoindex, custom-languages, hcl, dockerfile, bash, regex, chunking]

# Dependency graph
requires:
  - phase: none
    provides: foundation phase (no prior dependencies)
provides:
  - CustomLanguageSpec definitions for HCL, Dockerfile, Bash
  - DEVOPS_CUSTOM_LANGUAGES aggregated list
  - DevOps file patterns in IndexingConfig.include_patterns
affects:
  - 08-02 (language routing and flow integration needs these specs)
  - phase-2 metadata extraction (chunk boundaries must be correct)
  - phase-3 flow integration (passes DEVOPS_CUSTOM_LANGUAGES to SplitRecursively)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CustomLanguageSpec with standard Rust regex separators (no lookaheads)"
    - "Hierarchical separator levels (highest priority first)"

key-files:
  created:
    - src/cocosearch/indexer/languages.py
    - tests/indexer/test_languages.py
  modified:
    - src/cocosearch/indexer/config.py
    - tests/indexer/test_config.py

key-decisions:
  - "Standard Rust regex only -- no lookaheads/lookbehinds per research correction"
  - "HCL aliases tf and tfvars; hcl matches language_name directly"
  - "Dockerfile has no aliases -- routing handled by extract_language in Plan 02"
  - "Bash aliases sh, zsh, shell -- bash not in CocoIndex built-in list"
  - "Bare filename patterns for Dockerfile (may need **/ prefix if validation fails)"

patterns-established:
  - "CustomLanguageSpec: language_name + separators_regex + aliases pattern"
  - "Separator hierarchy: structural keywords > blank lines > newlines > whitespace"

# Metrics
duration: 2min
completed: 2026-01-27
---

# Phase 08 Plan 01: Language Definitions and DevOps Patterns Summary

**Three CustomLanguageSpec definitions (HCL, Dockerfile, Bash) with standard Rust regex separators and 8 DevOps file patterns in IndexingConfig**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-27T14:00:48Z
- **Completed:** 2026-01-27T14:02:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created `languages.py` with HCL_LANGUAGE (12 block keywords), DOCKERFILE_LANGUAGE (FROM at highest priority), and BASH_LANGUAGE (function keyword at Level 1)
- Added 8 DevOps file patterns to IndexingConfig (*.tf, *.hcl, *.tfvars, Dockerfile, Dockerfile.*, Containerfile, *.sh, *.bash)
- 25 new tests (21 language + 4 config) all passing, zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create languages.py with CustomLanguageSpec definitions** - `499862d` (feat)
2. **Task 2: Add DevOps file patterns to IndexingConfig** - `c021e6b` (feat)

## Files Created/Modified
- `src/cocosearch/indexer/languages.py` - Three CustomLanguageSpec constants and DEVOPS_CUSTOM_LANGUAGES list
- `tests/indexer/test_languages.py` - 21 tests covering specs, aliases, separators, regex guards
- `src/cocosearch/indexer/config.py` - Added 8 DevOps file patterns to include_patterns
- `tests/indexer/test_config.py` - 4 new tests for DevOps patterns and regression check

## Decisions Made
- Used standard Rust regex only (non-capturing groups, alternation) per research correction that CocoIndex uses `regex` v1.12.2, not `fancy-regex`
- HCL Level 1 separator covers all 12 top-level block keywords in a single alternation pattern
- Dockerfile FROM is a separate higher-priority separator from other instructions (Level 1 vs Level 2)
- Bash `function` keyword at Level 1; `func_name()` pattern deferred (would need lookaheads)
- Bare filename patterns used for Dockerfile/Containerfile (confidence LOW per research; Plan 02 validates)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Language specs ready for Plan 02 to wire into `SplitRecursively` via `custom_languages` parameter
- File patterns ready for indexing pipeline to pick up DevOps files
- `extract_language` function (replacing `extract_extension`) is next step in Plan 02
- Bare filename pattern validation (Dockerfile, Containerfile) needed in Plan 02

---
*Phase: 08-custom-language-definitions-and-file-routing*
*Completed: 2026-01-27*
