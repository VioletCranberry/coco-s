---
phase: 30-symbol-search-filters
plan: 03
subsystem: api
tags: [cli, mcp, argparse, symbol-filtering]

# Dependency graph
requires:
  - phase: 30-02
    provides: search() function with symbol_type and symbol_name parameters
provides:
  - CLI --symbol-type and --symbol-name flags for symbol filtering
  - MCP search_code with symbol_type and symbol_name parameters
  - MCP response always includes symbol metadata (type, name, signature)
affects: [documentation, user-guides]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "action=append for multi-value CLI flags"
    - "Annotated[str | list[str]] for MCP union types"

key-files:
  created: []
  modified:
    - src/cocosearch/cli.py
    - src/cocosearch/mcp/server.py
    - tests/unit/test_cli.py

key-decisions:
  - "CLI --symbol-type uses action=append for OR filtering"
  - "MCP symbol_type accepts both str and list[str] for flexibility"
  - "MCP response always includes symbol_type, symbol_name, symbol_signature (None if unavailable)"
  - "ValueError from search() returns structured MCP error with message field"

patterns-established:
  - "Multi-value CLI flags: action=append with dest parameter"
  - "MCP union types: str | list[str] | None with Field description"

# Metrics
duration: 2min
completed: 2026-02-03
---

# Phase 30 Plan 03: CLI and MCP Symbol Filter Integration Summary

**CLI --symbol-type and --symbol-name flags plus MCP parameters expose symbol filtering to users via both interfaces**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-03T11:16:53Z
- **Completed:** 2026-02-03T11:19:15Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added CLI --symbol-type flag with action=append for OR filtering (e.g., --symbol-type function --symbol-type method)
- Added CLI --symbol-name flag for glob pattern matching (case-insensitive)
- Added MCP symbol_type parameter accepting str or list[str]
- Added MCP symbol_name parameter for glob patterns
- MCP response always includes symbol metadata (symbol_type, symbol_name, symbol_signature)
- MCP returns structured error response when symbol filter fails
- 7 new CLI argument parsing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CLI --symbol-type and --symbol-name flags** - `02bd3fb` (feat)
2. **Task 2: Add MCP symbol_type and symbol_name parameters** - `6541c0b` (feat)
3. **Task 3: Add CLI argument parsing tests** - `7b150d8` (test)

## Files Created/Modified
- `src/cocosearch/cli.py` - Added --symbol-type (action=append) and --symbol-name flags, passed to search() call
- `src/cocosearch/mcp/server.py` - Added symbol_type and symbol_name parameters, error handling, symbol metadata in response
- `tests/unit/test_cli.py` - Added TestSymbolFilterArguments class with 7 tests

## Decisions Made
- CLI --symbol-type uses action=append to allow multiple values (creates list for OR filtering)
- MCP symbol_type accepts both str and list[str] for API flexibility (MCP clients may send either)
- MCP response always includes symbol_type, symbol_name, symbol_signature fields (None if not available)
- ValueError from search() (invalid type or pre-v1.7 index) returns structured error with "error", "message", and empty "results" array

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Symbol filtering is fully exposed through CLI and MCP interfaces
- Users can filter by --symbol-type function/class/method/interface
- Users can filter by --symbol-name pattern (glob with * and ?)
- Pre-v1.7 indexes show helpful "Re-index" error message in both CLI and MCP
- Phase 30 symbol filtering feature is complete pending final testing

---
*Phase: 30-symbol-search-filters*
*Completed: 2026-02-03*
