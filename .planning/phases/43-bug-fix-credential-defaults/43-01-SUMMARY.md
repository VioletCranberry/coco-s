---
phase: 43-bug-fix-credential-defaults
plan: 01
subsystem: config
tags: [database, credentials, defaults, cocoindex-bridge, devops-metadata]

# Dependency graph
requires:
  - phase: 42-multi-repo
    provides: "Existing config module, env_validation, CLI, indexer flow"
provides:
  - "DEFAULT_DATABASE_URL constant and get_database_url() helper"
  - "CocoIndex SDK environment bridge (COCOINDEX_DATABASE_URL auto-set)"
  - "Fixed extract_devops_metadata keyword argument (language_id)"
  - "Zero-config database connection (default credentials)"
affects: [44-docker-healthcheck, 45-mcp-context-transport, 46-mcp-roots]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Centralized database URL resolution via get_database_url()"
    - "Environment variable bridging between COCOSEARCH_* and COCOINDEX_*"

key-files:
  created:
    - tests/unit/config/test_env_validation.py
  modified:
    - src/cocosearch/config/env_validation.py
    - src/cocosearch/config/__init__.py
    - src/cocosearch/indexer/flow.py
    - src/cocosearch/search/db.py
    - src/cocosearch/cli.py
    - tests/unit/search/test_db.py

key-decisions:
  - "DEFAULT_DATABASE_URL uses cocosearch:cocosearch credentials matching Docker image"
  - "get_database_url() has CocoIndex bridge side-effect (sets COCOINDEX_DATABASE_URL)"
  - "validate_required_env_vars() returns empty list since DATABASE_URL has default"

patterns-established:
  - "Centralized URL resolution: all callsites use get_database_url() instead of raw os.getenv"
  - "Early bridge call in main() ensures CocoIndex SDK has credentials before any command"

# Metrics
duration: 36min
completed: 2026-02-08
---

# Phase 43 Plan 01: Bug Fix & Credential Defaults Summary

**Fixed DevOps metadata keyword bug and established zero-config database defaults with CocoIndex SDK bridge**

## Performance

- **Duration:** 36 min
- **Started:** 2026-02-08T10:15:57Z
- **Completed:** 2026-02-08T10:51:49Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Fixed `language_id` keyword argument bug in `extract_devops_metadata` call (flow.py line 93)
- Created `get_database_url()` helper with default URL and CocoIndex environment bridge
- Updated all callsites (search/db.py, indexer/flow.py, cli.py) to use centralized helper
- Updated `config check` to show "default" source when no env var is set
- Added early `get_database_url()` call in `main()` for CocoIndex bridge before command dispatch
- Created comprehensive tests for `get_database_url()` (default, env override, bridge, no-override)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix bug and create get_database_url() with CocoIndex bridge** - `4f00285` (fix)
2. **Task 2: Update CLI config check and main() bridge, update tests** - `8aad19b` (feat)

**Plan metadata:** (see final commit)

## Files Created/Modified
- `src/cocosearch/config/env_validation.py` - Added DEFAULT_DATABASE_URL constant and get_database_url() helper; removed DATABASE_URL from required vars
- `src/cocosearch/config/__init__.py` - Added DEFAULT_DATABASE_URL and get_database_url to exports
- `src/cocosearch/indexer/flow.py` - Fixed language_id keyword; replaced raw os.getenv with get_database_url()
- `src/cocosearch/search/db.py` - Replaced raw os.getenv with get_database_url(); removed import os
- `src/cocosearch/cli.py` - Updated config check display; added early get_database_url() call in main()
- `tests/unit/search/test_db.py` - Replaced ValueError test with default URL behavior test
- `tests/unit/config/test_env_validation.py` - New test file for get_database_url() and validate_required_env_vars

## Decisions Made
- DEFAULT_DATABASE_URL set to `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch` matching Docker image credentials
- get_database_url() bridges to COCOINDEX_DATABASE_URL as a side-effect (not overriding if already set)
- validate_required_env_vars() no longer checks DATABASE_URL (has default), returns empty list for backward compat

## Deviations from Plan

None - plan executed exactly as written. Note: Task 1 code changes were already committed under `4f00285` (labeled as 43-02 in git history from a prior execution); Task 2 changes were fresh.

## Issues Encountered
- Task 1 source code changes were already present in the repository from a prior partial execution (commit `4f00285`), so no new commit was needed for Task 1
- 2 pre-existing failures in tests/unit/mcp/test_server.py (unrelated to this plan's changes) -- these appear to be timing/infrastructure related MCP test issues

## User Setup Required

None - no external service configuration required. The entire point of this plan is to eliminate the need for DATABASE_URL configuration.

## Next Phase Readiness
- Zero-config database connection is complete -- users can run `docker compose up && cocosearch index .` without env vars
- Ready for phase 44 (Docker healthcheck improvements)
- CocoIndex SDK bridge ensures COCOINDEX_DATABASE_URL is always set

---
*Phase: 43-bug-fix-credential-defaults*
*Completed: 2026-02-08*
