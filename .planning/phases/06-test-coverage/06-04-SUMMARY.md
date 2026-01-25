---
phase: 06-test-coverage
plan: 04
subsystem: testing
tags: [pytest, cli, unittest.mock, argparse, capsys]

# Dependency graph
requires:
  - phase: 05-test-infrastructure
    provides: mock fixtures (mock_db_pool, mock_code_to_embedding, make_search_result)
provides:
  - CLI command tests (index, search, list, stats, clear)
  - Utility function tests (derive_index_name, parse_query_filters)
  - Error handling tests for CLI
affects: [06-test-coverage, test-maintenance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Mock at CLI boundary (patch imported functions, not internals)
    - pytest capsys for stdout/stderr capture
    - argparse.Namespace for direct command function testing

key-files:
  created:
    - tests/test_cli.py
  modified: []

key-decisions:
  - "Mock at CLI level (patch cocosearch.cli.search, not internal DB functions)"
  - "Test commands directly via command functions, not CLI parsing"
  - "Use capsys for output verification, not rich console mocking"

patterns-established:
  - "CLI test pattern: patch cocoindex.init + patch command dependencies"
  - "JSON output tests: capture with capsys, json.loads for validation"
  - "Error tests: verify exit code 1 and error key in JSON output"

# Metrics
duration: 3min
completed: 2026-01-25
---

# Phase 6 Plan 04: CLI Tests Summary

**Comprehensive CLI tests covering all 5 commands with mocked dependencies and JSON output validation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-25T22:45:38Z
- **Completed:** 2026-01-25T22:48:32Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Created 18 CLI tests covering all command paths
- Tests run without real database or Ollama connections
- Verified JSON output is parseable for all commands
- Error handling tested with appropriate exit codes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests for derive_index_name and parse_query_filters** - `5cf4019` (test)
2. **Task 2: Create tests for index, search, and list commands** - `6149809` (test)
3. **Task 3: Create tests for stats and clear commands, verify all CLI tests** - `8c82d8b` (test)

## Files Created/Modified
- `tests/test_cli.py` - 265 lines, 18 tests covering all CLI commands

## Test Coverage

| Class | Tests | Coverage |
|-------|-------|----------|
| TestDeriveIndexName | 5 | Path sanitization, edge cases |
| TestParseQueryFilters | 3 | Query filter extraction |
| TestIndexCommand | 2 | Invalid path, valid indexing |
| TestSearchCommand | 2 | Query required, JSON output |
| TestListCommand | 1 | JSON list output |
| TestStatsCommand | 2 | Specific index, nonexistent error |
| TestClearCommand | 2 | Force delete, nonexistent error |
| TestErrorHandling | 1 | Search error returns JSON error |

## Decisions Made
- **Mock at CLI level:** Patching `cocosearch.cli.search` instead of internal DB functions is cleaner and tests the command handler in isolation
- **Direct command testing:** Testing command functions directly with argparse.Namespace is faster than invoking CLI parser
- **capsys over rich mocking:** Using pytest's capsys fixture is simpler than mocking Rich console for output capture

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TestListCommand to mock at CLI level**
- **Found during:** Task 2 (list command tests)
- **Issue:** Original test tried to mock database pool, but list_command calls list_indexes which is already imported
- **Fix:** Changed to patch `cocosearch.cli.list_indexes` directly
- **Files modified:** tests/test_cli.py
- **Verification:** All tests pass
- **Committed in:** `8c82d8b` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test fix, no scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI tests complete, ready for MCP server tests
- All TEST-CLI-01 through TEST-CLI-03 requirements fulfilled
- Test fixtures from Phase 5 working well for CLI mocking

---
*Phase: 06-test-coverage*
*Completed: 2026-01-25*
