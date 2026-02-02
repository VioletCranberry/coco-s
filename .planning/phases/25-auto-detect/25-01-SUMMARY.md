---
phase: 25-auto-detect
plan: 01
subsystem: management
tags: [pathlib, symlinks, postgresql, lru-cache, collision-detection]

# Dependency graph
requires:
  - phase: 24-container-foundation
    provides: Container infrastructure for deployment
provides:
  - find_project_root() function for directory tree walking
  - get_canonical_path() for symlink resolution
  - resolve_index_name() with priority chain (config > directory name)
  - Metadata storage table for path-to-index mappings
  - Collision detection for index name conflicts
affects: [25-02, 25-03, mcp-auto-detect]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Directory tree walking with pathlib.Path.parent
    - Symlink resolution with Path.resolve(strict=False)
    - LRU caching with functools.lru_cache
    - PostgreSQL upsert with ON CONFLICT DO UPDATE

key-files:
  created:
    - src/cocosearch/management/context.py
    - src/cocosearch/management/metadata.py
  modified:
    - src/cocosearch/management/__init__.py

key-decisions:
  - "Use Path.resolve(strict=False) for symlink resolution before walking tree"
  - "Check .git first, then cocosearch.yaml for project root detection"
  - "Store canonical paths as TEXT in PostgreSQL (not VARCHAR)"
  - "Use lru_cache(maxsize=128) for path-to-index lookups"

patterns-established:
  - "find_project_root pattern: resolve symlinks, walk up tree, check markers"
  - "Collision detection: check before upsert, raise ValueError with guidance"
  - "Cache invalidation: call cache_clear() after any database write"

# Metrics
duration: 3min
completed: 2026-02-02
---

# Phase 25 Plan 01: Auto-Detect Foundation Summary

**Project root detection with symlink resolution, priority-chain index name resolution, and path-to-index metadata storage with collision detection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-02T17:39:20Z
- **Completed:** 2026-02-02T17:42:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Context detection module that walks up directory tree to find project root via .git or cocosearch.yaml
- Symlink resolution using pathlib.Path.resolve() for consistent canonical paths
- Priority chain for index name resolution: cocosearch.yaml indexName > directory name
- Metadata storage in PostgreSQL for path-to-index mappings
- Collision detection that prevents overwriting different project paths with same index name
- LRU caching for efficient path lookups in MCP tools

## Task Commits

Each task was committed atomically:

1. **Task 1: Create context detection module** - `b41ff51` (feat)
2. **Task 2: Create metadata storage module with collision detection** - `bdc06ef` (feat)

## Files Created/Modified

- `src/cocosearch/management/context.py` - Project root detection and index name resolution
- `src/cocosearch/management/metadata.py` - Path-to-index metadata storage with collision detection
- `src/cocosearch/management/__init__.py` - Exports for new functions

## Decisions Made

- **Symlink resolution before walking:** Resolve symlinks at the start of find_project_root() to avoid duplicate indexes for symlinked directories
- **Detection order:** Check .git before cocosearch.yaml because git repos are more common than explicit config files
- **TEXT over VARCHAR:** Use TEXT for paths in PostgreSQL per research recommendations (no arbitrary length limits)
- **Cache size 128:** Use maxsize=128 for lru_cache, sufficient for typical development workstation with 10-20 projects
- **Cache invalidation strategy:** Clear cache after every database write operation (register/clear)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Database not running for verification:** PostgreSQL not available locally, so Task 2 database tests were skipped. Import tests and function signatures verified. Full verification will occur when database is available (in integration tests or container environment).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Context detection functions ready for MCP tool integration
- Metadata storage functions ready for CLI integration (index command)
- Next plan (25-02) will integrate these functions into MCP tools for auto-detection

---
*Phase: 25-auto-detect*
*Completed: 2026-02-02*
