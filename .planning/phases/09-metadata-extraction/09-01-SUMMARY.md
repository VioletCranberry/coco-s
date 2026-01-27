---
phase: 09-metadata-extraction
plan: 01
subsystem: indexer
tags: [metadata, regex, hcl, dockerfile, bash, dataclass, cocoindex]
dependency-graph:
  requires:
    - "08-custom-languages (CustomLanguageSpec definitions, extract_language)"
  provides:
    - "DevOpsMetadata dataclass"
    - "extract_devops_metadata op function"
    - "Per-language extractors (HCL, Dockerfile, Bash)"
  affects:
    - "Phase 3: Flow Integration (wires metadata into flow)"
    - "Phase 4: Search and Output (surfaces metadata in results)"
tech-stack:
  added: []
  patterns:
    - "@dataclass return type from @cocoindex.op.function()"
    - "Module-level compiled regex for performance"
    - "Comment stripping before keyword matching"
    - "Dispatch map pattern for language routing"
key-files:
  created:
    - src/cocosearch/indexer/metadata.py
    - tests/indexer/test_metadata.py
  modified:
    - src/cocosearch/indexer/__init__.py
decisions:
  - id: "match-at-chunk-start"
    choice: "Match block keywords only at chunk start (after comment stripping)"
    rationale: "Phase 1 separators place keywords at chunk boundaries; mid-chunk keywords are nested blocks"
  - id: "language-as-parameter"
    choice: "Language identifier passed as parameter, not auto-detected"
    rationale: "Cleaner architecture; extract_language already handles routing in embedder.py"
  - id: "non-from-empty-hierarchy"
    choice: "Dockerfile non-FROM instructions get empty hierarchy in v1.2"
    rationale: "Stage context inheritance requires inter-chunk state, out of scope for v1.2"
  - id: "empty-string-for-unrecognized"
    choice: "Top-level Bash code and unrecognized DevOps chunks get empty block_type/hierarchy"
    rationale: "Consistent with non-DevOps files; language_id still populated for known DevOps files"
metrics:
  duration: "5m 27s"
  completed: "2026-01-27"
  tests-added: 53
  tests-total: 153
  lines-of-code: 252
  test-lines: 380
---

# Phase 09 Plan 01: Metadata Extraction Module Summary

**Standalone regex-based metadata extraction for HCL, Dockerfile, and Bash chunks with DevOpsMetadata dataclass returning block_type, hierarchy, and language_id.**

## What Was Done

### Task 1: Create metadata.py with DevOpsMetadata dataclass and extraction functions
- Created `src/cocosearch/indexer/metadata.py` (252 lines)
- `DevOpsMetadata` dataclass with `block_type`, `hierarchy`, `language_id` fields
- 8 module-level compiled regex patterns (3 comment patterns, 4 block extraction patterns, 1 FROM detail pattern)
- `_strip_leading_comments()` helper to prevent false positives from comment lines containing keywords
- 3 per-language extraction functions: `extract_hcl_metadata`, `extract_dockerfile_metadata`, `extract_bash_metadata`
- Dispatch maps (`_LANGUAGE_DISPATCH`, `_LANGUAGE_ID_MAP`) for routing and language normalization
- `extract_devops_metadata` decorated with `@cocoindex.op.function()` for flow integration
- Commit: `fbf5f30`

### Task 2: Create test_metadata.py and update __init__.py exports
- Created `tests/indexer/test_metadata.py` (380 lines, 53 tests across 7 test classes)
- Test coverage includes all 12 HCL block keywords (0/1/2 label variants), all 3 Bash function syntaxes, Dockerfile FROM with/without AS and --platform
- Edge cases: comment stripping (HCL #, //, /* */), leading whitespace, false positive prevention, dispatch map completeness
- Updated `__init__.py` with `DevOpsMetadata` and `extract_devops_metadata` exports
- Commit: `da7fede`

## Verification Results

All 6 verification checks passed:
1. `python -m pytest tests/indexer/test_metadata.py -v` -- 53/53 passed
2. `python -m pytest tests/indexer/ -v` -- 153/153 passed (no regressions)
3. Direct imports from `cocosearch.indexer.metadata` -- OK
4. Package-level exports from `cocosearch.indexer` -- OK
5. Roadmap success criteria smoke tests -- all 3 passed
6. False positive test (comment containing "resource") -- correctly returns empty block_type

## Success Criteria Status

| Requirement | Status | Verified By |
|-------------|--------|-------------|
| REQ-07: HCL block type extraction (12 keywords) | PASS | 12 tests covering all keywords |
| REQ-08: HCL hierarchy (0/1/2 labels) | PASS | resource, module, terraform tests |
| REQ-09: Dockerfile instruction extraction | PASS | FROM, RUN, COPY, ENV tests |
| REQ-10: Dockerfile FROM stage/image hierarchy | PASS | AS, no-AS, --platform, scratch tests |
| REQ-11: Bash function name (3 syntaxes) | PASS | POSIX, ksh, hybrid tests |
| REQ-12: @cocoindex.op.function() decorator | PASS | Import verification |
| REQ-13: Non-DevOps empty strings | PASS | Python file + empty language tests |
| Module-level regex compilation | PASS | Code inspection |
| Comment stripping prevents false positives | PASS | 3 comment type tests + false positive test |
| Module exports available | PASS | Package-level import verification |

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Match at chunk start only** -- Block keywords matched only at the start of chunk text (after stripping leading comments and whitespace). Mid-chunk keywords are nested blocks or string content and should not define the chunk's identity.

2. **Language as parameter** -- The `extract_devops_metadata` function receives the language identifier as a parameter rather than auto-detecting it. This keeps the module standalone and relies on `extract_language()` from `embedder.py` for routing.

3. **Non-FROM empty hierarchy** -- Dockerfile instructions other than FROM get empty hierarchy in v1.2. Stage context inheritance would require inter-chunk state tracking, which is deferred.

4. **Top-level Bash gets empty metadata** -- Non-function Bash chunks (top-level code, control flow) get empty `block_type` and `hierarchy`, consistent with the empty-strings-over-NULLs convention.

## Next Phase Readiness

Phase 3 (Flow Integration and Schema) can proceed. It needs:
- `extract_devops_metadata` function from `metadata.py` (available)
- `DevOpsMetadata` dataclass structure (available: block_type, hierarchy, language_id)
- The function signature `extract_devops_metadata(text: str, language: str) -> DevOpsMetadata` is stable

No blockers identified for Phase 3.
