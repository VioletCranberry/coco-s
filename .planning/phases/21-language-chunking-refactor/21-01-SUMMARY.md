---
phase: 21-language-chunking-refactor
plan: 01
subsystem: architecture
tags: [protocol, registry, plugin-architecture, cocoindex]

# Dependency graph
requires:
  - phase: 08-custom-language-definitions-and-file-routing
    provides: CustomLanguageSpec and metadata extraction patterns for DevOps languages
provides:
  - handlers/ package with Protocol-based plugin architecture
  - Autodiscovery registry for language handlers
  - extract_devops_metadata() CocoIndex transform function
  - TextHandler fallback for unrecognized extensions
  - Template for creating new language handlers
affects: [21-02, 21-03, future-language-extensions]

# Tech tracking
tech-stack:
  added: []
  patterns: [Protocol-based plugin architecture, pathlib.glob autodiscovery, fail-fast extension registry]

key-files:
  created:
    - src/cocosearch/handlers/__init__.py
    - src/cocosearch/handlers/text.py
    - src/cocosearch/handlers/_template.py
  modified: []

key-decisions:
  - "Protocol uses SEPARATOR_SPEC and extract_metadata() instead of chunk() because CocoIndex transforms run in Rust"
  - "Handlers export CustomLanguageSpec for CocoIndex chunking, not Python-based chunking"
  - "extract_devops_metadata() decorated with @cocoindex.op.function() for flow.py integration"
  - "Extension registry uses fail-fast ValueError on conflicts at module import time"
  - "TextHandler returns empty metadata and relies on CocoIndex default text splitting"

patterns-established:
  - "LanguageHandler Protocol: structural subtyping with EXTENSIONS, SEPARATOR_SPEC, extract_metadata()"
  - "Autodiscovery pattern: pathlib.glob('*.py') + importlib + duck typing validation"
  - "Shared types defined before discovery to avoid circular imports"

# Metrics
duration: 3min
completed: 2026-02-01
---

# Phase 21 Plan 01: Handlers Package Foundation Summary

**Protocol-based handler registry with autodiscovery, CocoIndex transform dispatcher, and text fallback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-01T03:38:48Z
- **Completed:** 2026-02-01T03:41:26Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- Created handlers/ package with LanguageHandler Protocol and registry autodiscovery
- Implemented extract_devops_metadata() CocoIndex transform function for flow.py integration
- Established TextHandler fallback for unrecognized extensions
- Provided _template.py with comprehensive documentation for adding new language handlers

## Task Commits

Each task was committed atomically:

1. **Task 1: Create handlers package with Protocol and registry** - `305121b` (feat)
2. **Task 2: Create default text handler and template** - `0340ad9` (feat)

## Files Created/Modified

- `src/cocosearch/handlers/__init__.py` - Protocol definition, autodiscovery registry, public API (get_handler, get_custom_languages, extract_devops_metadata)
- `src/cocosearch/handlers/text.py` - Default fallback handler for unrecognized extensions
- `src/cocosearch/handlers/_template.py` - Template for new language handlers with comprehensive TODOs

## Decisions Made

**Architecture Decision: Handlers provide specs, not chunking**
- Handlers export SEPARATOR_SPEC for CocoIndex's Rust-based chunking
- Handlers export extract_metadata() for Python-based metadata extraction
- This aligns with CocoIndex's transform execution model (chunking in Rust, metadata in Python)

**Discovery Pattern: Fail-fast at import**
- Registry discovery runs at module import time using pathlib.glob() + importlib
- Extension conflicts raise ValueError immediately with clear error message
- Catches configuration errors before indexing starts

**Protocol Pattern: Structural subtyping**
- LanguageHandler Protocol defines interface without requiring inheritance
- Handlers discovered via duck typing (hasattr checks)
- Enables clean plugin architecture without coupling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready for Plan 21-02:** Migrate HCL, Dockerfile, and Bash handlers from indexer/languages.py and indexer/metadata.py into handlers/ package structure.

**Registry is empty:** Currently no language handlers registered (expected). Plan 21-02 will populate the registry with HCL, Dockerfile, and Bash handlers.

**Integration point prepared:** extract_devops_metadata() function is ready to be imported by flow.py in Plan 21-03.

---
*Phase: 21-language-chunking-refactor*
*Completed: 2026-02-01*
