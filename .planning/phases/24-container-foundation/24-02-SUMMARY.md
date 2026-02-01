---
phase: 24-container-foundation
plan: 02
subsystem: infra
tags: [s6-overlay, s6-rc, postgresql, ollama, docker, process-supervision]

# Dependency graph
requires:
  - phase: 24-01
    provides: Dockerfile with s6-overlay, service registrations in user/contents.d
provides:
  - PostgreSQL longrun service with readiness notification
  - Ollama longrun service with readiness notification
  - MCP server longrun service with dependency ordering
  - Ollama model warmup oneshot
  - Service dependency chain ensuring startup order
affects: [24-03, 25-auto-detect, docker-runtime]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "s6-rc longrun services with notification-fd for readiness"
    - "s6-notifyoncheck for polling-based readiness"
    - "dependencies.d empty files for service ordering"
    - "oneshot services for initialization tasks"

key-files:
  created:
    - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/
    - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-ollama/
    - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/
    - docker/rootfs/etc/s6-overlay/s6-rc.d/init-warmup/
    - docker/rootfs/etc/s6-overlay/scripts/warmup-ollama
  modified: []

key-decisions:
  - "PostgreSQL uses pg_isready for readiness checks (actual connection acceptance)"
  - "Ollama uses /api/tags endpoint for readiness (API available)"
  - "MCP depends on PostgreSQL, Ollama, AND warmup (model loaded before requests)"
  - "Warmup is non-blocking failure (model loads on first request if warmup fails)"
  - "PostgreSQL shutdown uses -m fast via finish script for clean shutdown"

patterns-established:
  - "s6-rc service structure: type, run, notification-fd, data/check, dependencies.d/"
  - "Readiness via s6-notifyoncheck with configurable polling intervals"
  - "Dependency chain: dependencies.d/service-name empty files"
  - "Scripts directory for oneshot commands: /etc/s6-overlay/scripts/"

# Metrics
duration: 6min
completed: 2026-02-01
---

# Phase 24 Plan 02: s6-rc Service Definitions Summary

**PostgreSQL, Ollama, and MCP longrun services with s6-notifyoncheck readiness and dependency ordering for correct startup sequence**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-01T19:37:36Z
- **Completed:** 2026-02-01T19:43:30Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments

- PostgreSQL longrun service with data directory initialization, user/database creation, and pg_isready readiness
- Ollama longrun service with /api/tags readiness check and 120-attempt polling
- MCP server longrun service with triple dependency on PostgreSQL, Ollama, and warmup
- Ollama model warmup oneshot that preloads nomic-embed-text into memory

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PostgreSQL longrun service with readiness notification** - `dc23348` (feat)
2. **Task 2: Create Ollama longrun service with readiness notification and warmup oneshot** - `560c41b` (feat)
3. **Task 3: Create MCP server longrun service with dependencies** - `8043508` (feat, included with health-check)

## Files Created/Modified

### PostgreSQL Service (`svc-postgresql/`)
- `type` - Service type: longrun
- `run` - Initialization and startup script with s6-notifyoncheck
- `finish` - Clean shutdown with pg_ctl -m fast
- `notification-fd` - Readiness notification file descriptor: 3
- `data/check` - Readiness check: pg_isready

### Ollama Service (`svc-ollama/`)
- `type` - Service type: longrun
- `run` - Startup script with s6-notifyoncheck (120 attempts, 2s intervals)
- `notification-fd` - Readiness notification file descriptor: 3
- `data/check` - Readiness check: curl /api/tags

### MCP Service (`svc-mcp/`)
- `type` - Service type: longrun
- `run` - Start MCP server with configurable transport/port
- `dependencies.d/svc-postgresql` - Depends on PostgreSQL
- `dependencies.d/svc-ollama` - Depends on Ollama
- `dependencies.d/init-warmup` - Depends on model warmup

### Warmup Service (`init-warmup/`)
- `type` - Service type: oneshot
- `up` - Path to warmup script
- `dependencies.d/svc-ollama` - Runs after Ollama ready

### Scripts
- `scripts/warmup-ollama` - Preloads embedding model with retry logic

## Decisions Made

1. **PostgreSQL readiness via pg_isready** - Checks actual connection acceptance, not just process running
2. **Ollama readiness via /api/tags** - Community-consensus endpoint for API availability
3. **MCP depends on warmup** - Ensures model is loaded before accepting MCP requests for fast first response
4. **Warmup non-blocking failure** - Returns 0 even on failure; model will load on first real request
5. **PostgreSQL fast shutdown** - finish script uses `pg_ctl stop -m fast` for predictable container shutdown

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all s6-rc service definitions created without issues. Docker image builds successfully with service files in rootfs overlay.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All s6-rc services defined with proper dependency ordering
- Docker image builds successfully with rootfs overlay
- Ready for Plan 03: health-check endpoint and container testing
- Service startup order: PostgreSQL -> Ollama -> init-warmup -> svc-mcp

---
*Phase: 24-container-foundation*
*Completed: 2026-02-01*
