---
phase: 25-auto-detect
plan: 02
subsystem: mcp
tags: [mcp, auto-detect, fastmcp, collision-detection, path-registration]

# Dependency graph
requires:
  - phase: 25-01
    provides: find_project_root, resolve_index_name, get_index_metadata, register_index_path
provides:
  - MCP search_code with optional index_name parameter
  - Auto-detection from current working directory in MCP tools
  - Structured error responses for all failure modes
  - Path registration during MCP indexing
affects: [25-03, mcp-integration-tests, user-facing-search]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - MCP tool returns structured error dict instead of raising exceptions
    - Auto-detection with fallback to explicit parameter
    - Path registration after successful indexing

key-files:
  created: []
  modified:
    - src/cocosearch/mcp/server.py

key-decisions:
  - "Return structured error dicts (not exceptions) from MCP tools for LLM interpretation"
  - "Check index existence in list_indexes before attempting search"
  - "Collision check uses metadata canonical_path comparison"
  - "Management layer handles metadata cleanup (not MCP layer) for DRY"

patterns-established:
  - "MCP auto-detect: find_project_root -> resolve_index_name -> check existence -> collision check -> proceed"
  - "Error response format: {error: type, message: guidance, results: []}"

# Metrics
duration: 3min
completed: 2026-02-02
---

# Phase 25 Plan 02: MCP Auto-Detect Integration Summary

**MCP search_code now accepts optional index_name, auto-detecting from cwd with structured error responses for all failure modes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-02T21:46:00Z
- **Completed:** 2026-02-02T21:49:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Made search_code index_name parameter optional with auto-detection from current working directory
- Added structured error responses for: no project detected, index not found, index name collision
- Added path registration to index_codebase MCP tool after successful indexing
- Integrated with management layer for metadata cleanup during clear operations

## Task Commits

Each task was committed atomically:

1. **Task 1: Make search_code index_name optional with auto-detection** - `0d3fb6b` (feat)
2. **Task 2: Add collision detection in auto-detect flow** - `dd17449` (feat)

## Files Created/Modified

- `src/cocosearch/mcp/server.py` - Added auto-detection to search_code, path registration to index_codebase

## Decisions Made

- **Structured error responses:** MCP tools return error dicts instead of raising exceptions, allowing the LLM to interpret and present errors to users
- **Index existence check:** Query list_indexes and compare against set of names for O(n) check before search
- **Collision detection:** Compare canonical_path from metadata against current project's resolved path
- **DRY metadata cleanup:** Management layer's clear_index handles clear_index_path, so MCP layer doesn't duplicate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used management layer for metadata cleanup instead of MCP layer**
- **Found during:** Task 2 (collision detection integration)
- **Issue:** Plan specified adding clear_index_path to MCP clear_index, but management clear_index already does this
- **Fix:** Removed duplicate call from MCP layer, added comment explaining mgmt layer handles it
- **Files modified:** src/cocosearch/mcp/server.py
- **Verification:** Confirmed clear_index_path in management/clear.py source
- **Committed in:** dd17449 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (blocking - avoided duplication)
**Impact on plan:** Minor architectural improvement, no scope change

## Issues Encountered

- Previous session had already committed CLI path registration (25-03 work) but STATE.md not updated - proceeded with MCP-specific changes only

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MCP search_code now fully supports auto-detection
- Path registration happens during both CLI indexing (25-03 commit) and MCP indexing (this plan)
- Ready for end-to-end testing of auto-detect workflow
- Next plan should verify complete flow: index project -> search without index_name -> collision scenarios

---
*Phase: 25-auto-detect*
*Completed: 2026-02-02*
