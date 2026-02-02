# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-01)

**Core value:** Semantic code search that runs entirely locally -- no data leaves your machine.
**Current focus:** Phase 24 - Container Foundation (COMPLETE)

## Current Position

Milestone: v1.6 All-in-One Docker & Auto-Detect
Phase: 24 of 26 (Container Foundation)
Plan: 04 of 04 complete
Status: Phase complete
Last activity: 2026-02-02 -- Completed 24-04-PLAN.md (end-to-end verification)

Progress: [############################################------------] 64/? (v1.6 plans TBD)

## Milestones Shipped

| Milestone | Phases | Plans | Shipped |
|-----------|--------|-------|---------|
| v1.0 MVP | 1-4 | 11 | 2026-01-25 |
| v1.1 Docs & Tests | 5-7 | 11 | 2026-01-26 |
| v1.2 DevOps Language Support | 8-10, 4-soi | 6 | 2026-01-27 |
| v1.3 Docker Integration Tests | 11-14 | 11 | 2026-01-30 |
| v1.4 Dogfooding Infrastructure | 15-18 | 7 | 2026-01-31 |
| v1.5 Configuration & Architecture Polish | 19-22 | 11 | 2026-02-01 |

**Total shipped:** 22 phases, 58 plans across 6 milestones
**v1.6 in progress:** Phase 23 complete (2 plans), Phase 24 complete (4 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 64
- Total execution time: ~8 days across 6 milestones

**By Milestone:**

| Milestone | Phases | Plans | Duration |
|-----------|--------|-------|----------|
| v1.0 | 1-4 | 11 | 2 days |
| v1.1 | 5-7 | 11 | 2 days |
| v1.2 | 8-10, 4-soi | 6 | 1 day |
| v1.3 | 11-14 | 11 | 1 day |
| v1.4 | 15-18 | 7 | 2 days |
| v1.5 | 19-22 | 11 | 1 day |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full list (33 decisions).

**Phase 23 decisions:**
- Configure FastMCP via mcp.settings instead of constructor params for dynamic host/port
- Use 0.0.0.0 as default host for container deployments
- Default port 3000 for network transports
- Patch cocosearch.mcp.run_server not cocosearch.cli.run_server (import inside function)
- Mock mcp.settings for transport configuration tests

**Phase 24-01 decisions:**
- Copy Ollama binary from model-downloader stage instead of downloading separately
- Map TARGETARCH to s6-overlay naming (arm64->aarch64, amd64->x86_64)
- Use official ollama/ollama image for multi-arch model baking (gerke74 is amd64-only)

**Phase 24-02 decisions:**
- PostgreSQL uses pg_isready for readiness checks (actual connection acceptance)
- Ollama uses /api/tags endpoint for readiness (API available)
- MCP depends on PostgreSQL, Ollama, AND warmup (model loaded before requests)
- Warmup is non-blocking failure (model loads on first request if warmup fails)
- PostgreSQL shutdown uses -m fast via finish script for clean shutdown

**Phase 24-03 decisions:**
- Use script-based HEALTHCHECK instead of inline commands for maintainability
- STOPSIGNAL SIGTERM cascades through s6-overlay to services
- init-ready depends on svc-mcp to ensure all services are ready

**Phase 24-04 decisions:**
- Exclude tests directory from build context (not needed in container)
- Fix Ollama model path from root to home directory in COPY instruction
- Install git in container for cocosearch CLI to detect repository metadata

### Pending Todos

None.

### Blockers/Concerns

None.

### Research Notes (v1.6)

Key findings from research phase:
- Use s6-overlay (not supervisord) for process supervision
- SSE deprecated but needed for Claude Desktop compatibility
- Streamable HTTP is MCP's future standard
- PID 1 signal handling critical for PostgreSQL data integrity
- Ollama cold start 30-120s, need warmup in entrypoint

## Session Continuity

Last session: 2026-02-02T16:48:27Z
Stopped at: Completed 24-04-PLAN.md (Phase 24 fully complete with E2E verification)
Resume file: None
Next action: Begin Phase 25 (Auto-detect project)

---
*Updated: 2026-02-02 after 24-04 complete*
