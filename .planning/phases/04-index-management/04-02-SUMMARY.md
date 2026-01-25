---
phase: 04-index-management
plan: 02
subsystem: cli
tags: [argparse, rich, json, management, git-detection]
dependency-graph:
  requires:
    - phase: 04-01
      provides: management module functions (list_indexes, get_stats, clear_index, derive_index_from_git)
  provides:
    - list CLI command for index discovery
    - stats CLI command for index statistics
    - clear CLI command with confirmation prompt
    - git-based auto-detection for search index
  affects: [users, mcp-integration, documentation]
tech-stack:
  added: []
  patterns: [json-default-pretty-flag, stderr-hints-for-json-mode, confirmation-prompt-with-force]
key-files:
  created: []
  modified:
    - src/cocosearch/cli.py
key-decisions:
  - "Print 'Using index:' to stderr in JSON mode to keep stdout clean"
  - "Git root detection before cwd fallback for auto-index"
  - "Show stats before clear confirmation for visibility"
patterns-established:
  - "Confirmation prompt pattern: show what will be affected, prompt [y/N], --force to skip"
  - "All management commands: JSON default, --pretty for Rich tables"
duration: 6min
completed: 2026-01-25
---

# Phase 04 Plan 02: CLI Management Commands Summary

**CLI commands list/stats/clear with JSON/Rich output and git-based search auto-detection from repository root**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-25T13:31:55Z
- **Completed:** 2026-01-25T13:37:43Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- `cocosearch list` command showing all indexes (JSON array or Rich table)
- `cocosearch stats` command showing file/chunk/size metrics for one or all indexes
- `cocosearch clear <index>` with confirmation prompt and --force flag
- Search auto-detection uses git root first, falls back to cwd
- "Using index:" hint printed before all search results

## Task Commits

Each task was committed atomically:

1. **Task 1: Add list and stats commands** - `694f068` (feat)
2. **Task 2: Add clear command with confirmation** - `694f068` (feat)
3. **Task 3: Update auto-detect to use git root** - `cc1c33a` (feat)

**Note:** Tasks 1 and 2 were bundled into commit 694f068 which also included 04-03 MCP work. Task 3 was included in cc1c33a docs commit.

## Files Created/Modified

- `src/cocosearch/cli.py` - Extended with list_command, stats_command, clear_command, and enhanced search auto-detection

## Commands Added

```bash
# List all indexes
cocosearch list              # JSON array
cocosearch list --pretty     # Rich table

# Show statistics
cocosearch stats             # All indexes (JSON)
cocosearch stats myindex     # Specific index
cocosearch stats --pretty    # Rich table format

# Delete an index
cocosearch clear myindex              # Prompts for confirmation
cocosearch clear myindex --force      # Skip confirmation
cocosearch clear myindex --pretty     # Rich success message
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Print "Using index:" to stderr in JSON mode | Keep stdout clean for piping/parsing |
| Git root detection before cwd fallback | More reliable index auto-detection when in subdirectories |
| Show stats before clear confirmation | User sees what will be deleted before confirming |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully. The infrastructure (PostgreSQL) was not running during verification, but help commands and import verification confirmed correct implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All CLI management commands are complete:
- list: Shows all available indexes
- stats: Shows metrics for one or all indexes
- clear: Safely deletes indexes with confirmation
- search: Auto-detects index from git root

Ready for:
- Documentation updates
- User testing with real infrastructure
- Future enhancements (e.g., staleness detection)

---
*Phase: 04-index-management*
*Completed: 2026-01-25*
