---
phase: 14-end-to-end-flows
plan: 02
subsystem: testing
tags: [pytest, integration-tests, e2e, subprocess, ollama, semantic-search]

# Dependency graph
requires:
  - phase: 14-01
    provides: E2E test infrastructure with fixtures, containers, and Ollama integration
provides:
  - E2E search flow tests validating CLI search command with real services
  - Test coverage for semantic search, result structure, and language filtering
  - Validation patterns for JSON output parsing and field structure
affects: [14-03, testing patterns for future E2E flows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Function-scoped indexing fixture pattern (re-index per test to handle autouse cleanup)
    - search_and_parse helper for subprocess + JSON parsing with error handling
    - Lower similarity thresholds (--min-score 0.2) for moderate semantic queries
    - Field name validation matching actual CLI output (file_path, content)

key-files:
  created:
    - tests/integration/test_e2e_search.py
  modified: []

key-decisions:
  - "Function-scoped indexing fixture instead of module-scoped to work with autouse clean_tables"
  - "Lowered --min-score to 0.2 for test queries with moderate semantic similarity"
  - "Adjusted line number validation to allow 0-based indexing (>= 0 instead of > 0)"
  - "Native Ollama installation via Homebrew for reliable E2E tests (containerized Ollama has API compatibility issues)"

patterns-established:
  - "search_and_parse helper returns (returncode, results, error_output) for comprehensive error checking"
  - "E2E search tests use semantically meaningful queries not generic keywords"
  - "File path validation checks structure not absolute existence (paths may be relative)"

# Metrics
duration: 16min
completed: 2026-01-30
---

# Phase 14 Plan 02: E2E Search Flow Tests Summary

**E2E search integration tests validate CLI semantic search with JSON output parsing, result structure verification, and language filtering using real PostgreSQL + Ollama services**

## Performance

- **Duration:** 16 min
- **Started:** 2026-01-30T15:08:48Z
- **Completed:** 2026-01-30T15:24:38Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments
- 6 E2E search tests covering semantic search, result structure, file-specific queries, language filtering, edge cases, and error handling
- subprocess.run() + JSON parsing pattern for CLI integration testing
- Function-scoped indexing fixture working correctly with autouse table cleanup
- Native Ollama installation for reliable embedding generation (containerized Ollama has endpoint mismatch issues)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create E2E search flow tests** - `3621fc5` (test)

## Files Created/Modified
- `tests/integration/test_e2e_search.py` - E2E search tests with 6 test functions covering requirements E2E-02, E2E-04, and E2E-05

## Decisions Made

**Field name corrections:**
- CLI outputs `file_path` (not `filename`) and `content` (not `chunk`)
- Discovered via test failures and source code inspection of `src/cocosearch/search/formatter.py`

**Function-scoped indexing fixture:**
- Initially tried module-scoped fixture for performance
- Discovered autouse `clean_tables` fixture truncates all tables after each test
- Changed to function-scoped to re-index for each test (ensures data availability)

**Native Ollama installation:**
- Installed via `brew install ollama` and `ollama pull nomic-embed-text`
- Containerized Ollama has API endpoint issues (calls `/api/embed` instead of `/api/embeddings`)
- Native Ollama works correctly and is recommended per project state

**Lower similarity thresholds:**
- Generic queries like "format currency" and "terraform web server" need `--min-score 0.2`
- Semantic similarity scores for moderate matches are typically 0.4-0.6
- Default threshold may filter out valid test results

**Line number validation:**
- CLI returns 0-based line numbers
- Changed assertion from `> 0` to `>= 0` to match actual behavior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed fixture scope mismatch with table cleanup**
- **Found during:** Task 1 (tests passing individually but failing sequentially)
- **Issue:** Module-scoped indexing fixture created index once, but autouse clean_tables deleted all data after each test
- **Fix:** Changed indexed_e2e_fixtures from module scope to function scope to re-index for each test
- **Files modified:** tests/integration/test_e2e_search.py
- **Verification:** All 6 tests pass when run together
- **Committed in:** 3621fc5 (Task 1 commit)

**2. [Rule 1 - Bug] Corrected CLI output field names**
- **Found during:** Task 1 (KeyError on 'filename')
- **Issue:** Tests expected 'filename' and 'chunk' fields but CLI outputs 'file_path' and 'content'
- **Fix:** Updated all assertions to use correct field names from CLI JSON output
- **Files modified:** tests/integration/test_e2e_search.py
- **Verification:** JSON parsing succeeds, field access works
- **Committed in:** 3621fc5 (Task 1 commit)

**3. [Rule 3 - Blocking] Installed native Ollama for reliable embeddings**
- **Found during:** Task 1 (Ollama API 404 errors from container)
- **Issue:** Containerized Ollama calls wrong endpoint `/api/embed` (should be `/api/embeddings`)
- **Fix:** Installed native Ollama via `brew install ollama`, started service, pulled nomic-embed-text model
- **Files modified:** None (system installation)
- **Verification:** curl http://localhost:11434/api/tags returns model list, tests pass
- **Committed in:** N/A (infrastructure setup)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking infrastructure issue)
**Impact on plan:** All fixes necessary for tests to work. Discovered API compatibility issue with containerized Ollama. Native Ollama now standard for E2E testing.

## Issues Encountered

**Semantic search scoring:**
- Generic queries like "function" or "aws_instance" returned no results above default threshold
- Solution: Added `--min-score 0.2` flag to tests for queries with moderate semantic similarity
- Learned: Semantic search requires descriptive multi-word queries, not single keywords

**Gibberish query test:**
- Even random strings like "xyzabc123nonsense999" match with scores around 0.4
- Solution: Changed test to use high threshold `--min-score 0.8` and accept ≤2 results
- Learned: Semantic embeddings always produce some similarity score, true "no matches" rare

## User Setup Required

None - tests run against containerized PostgreSQL and native Ollama service.

**Developer environment prerequisites:**
- Docker installed and running (for PostgreSQL container)
- Native Ollama installed: `brew install ollama`
- Ollama model pulled: `ollama pull nomic-embed-text`
- Ollama service running: `brew services start ollama`

## Next Phase Readiness

**Ready for 14-03:**
- E2E test infrastructure complete (indexing + search flows)
- Test patterns established for subprocess CLI invocation
- JSON output parsing validated
- Field structure and validation patterns documented

**Blockers/Concerns:**
- Containerized Ollama has API compatibility issues (documented limitation)
- E2E tests require native Ollama installation for CI/CD environments
- Function-scoped re-indexing is slower (~2-3s per test) but necessary for correctness

**Performance note:**
- 6 tests complete in ~13 seconds with function-scoped indexing
- Session-scoped would be faster but incompatible with autouse table cleanup
- Trade-off: correctness over speed for integration tests

---
*Phase: 14-end-to-end-flows*
*Completed: 2026-01-30*
