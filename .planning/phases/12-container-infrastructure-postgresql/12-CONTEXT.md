# Phase 12: Container Infrastructure & PostgreSQL - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Docker-based PostgreSQL testing with session-scoped containers and function-scoped cleanup. Validates real PostgreSQL+pgvector behavior in integration tests. Container starts once per test session, database state cleans between tests via TRUNCATE.

</domain>

<decisions>
## Implementation Decisions

### Container Lifecycle
- Session-scoped container — one PostgreSQL container for entire test run
- 60 second startup timeout — handles slow CI runners and first-time image pulls
- Pin exact image version (e.g., pgvector/pgvector:pg16) — reproducible builds, explicit upgrades

### Test Isolation
- TRUNCATE tables between tests — fast cleanup, keeps schema
- Shared database with cleaned tables — one database for all tests
- pgvector extension baked into container entrypoint — ready before tests connect
- Tests create their own schema as needed — explicit, each module sets up what it needs

### Configuration Approach
- Environment variables with defaults — override via env vars for CI flexibility
- Fixed port (e.g., 5433) — predictable, easy to debug, avoids conflict with local PostgreSQL on 5432
- Separate docker-compose.test.yml — container config in compose file, conftest reads it
- Fixed database name (e.g., cocosearch_test) — predictable, easy to inspect

### Failure Handling
- Fail immediately if Docker unavailable — hard error forces Docker availability
- Fail with diagnostic message on startup failure — show container logs, suggest fixes
- Keep containers on failure for debugging, clean up otherwise — inspect state after crashes
- Retry once with 1s backoff on connection loss — handles transient issues

### Claude's Discretion
- Health check implementation details (pg_isready vs TCP)
- Exact container naming convention
- TRUNCATE ordering for foreign key constraints
- Specific environment variable names

</decisions>

<specifics>
## Specific Ideas

- Port 5433 to avoid conflict with any local PostgreSQL on default 5432
- Container logs should be captured and shown on failure for easy debugging
- docker-compose.test.yml keeps container config separate from test logic

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-container-infrastructure-postgresql*
*Context gathered: 2026-01-30*
