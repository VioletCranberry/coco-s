# Phase 44: Docker Image Simplification - Research

**Researched:** 2026-02-08
**Domain:** Docker, s6-overlay process supervision, Dockerfile multi-stage builds
**Confidence:** HIGH

## Summary

This phase strips the CocoSearch application code from the Docker image, making it infrastructure-only (PostgreSQL+pgvector and Ollama+model). The operation is purely subtractive -- removing the Python builder stage, the svc-mcp s6 service, and all related configuration. The remaining services (svc-postgresql, svc-ollama, init-warmup) are unchanged.

The current Docker image has a 3-stage Dockerfile (model-downloader, python-builder, final runtime) with 5 s6-overlay services (svc-postgresql, svc-ollama, svc-mcp, init-warmup, init-ready). After simplification it will have a 2-stage Dockerfile (model-downloader, final runtime) with 4 s6-overlay services (svc-postgresql, svc-ollama, init-warmup, init-ready). The base image changes from `python:3.11-slim` to `debian:bookworm-slim` and PostgreSQL upgrades from 16 to 17.

The critical risk is leaving orphaned references to svc-mcp, which would crash the container at startup. The complete inventory of files to delete/modify is documented below.

**Primary recommendation:** Delete all svc-mcp files (6 files), remove python-builder stage, rewire init-ready dependencies, update health-check, switch base image, upgrade PostgreSQL. Update README and docs to reflect the new infra-only model.

## Standard Stack

The established tools/components for this domain:

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| s6-overlay | 3.2.2.0 (current in Dockerfile) | PID 1 init, process supervision | Already in use, proven for multi-process Docker containers |
| debian:bookworm-slim | latest | Base image (replacing python:3.11-slim) | No Python needed; saves ~80MB; clearer intent |
| PostgreSQL | 17 (upgrading from 16) | Database with pgvector | Aligns with docker-compose.yml which already uses pg17 |
| pgvector | via postgresql-17-pgvector apt package | Vector similarity search extension | Available in PostgreSQL APT repository for Debian bookworm |
| Ollama | latest (from ollama/ollama:latest) | Embedding model server | Already in use, unchanged |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| uvx | via uv package | Run CocoSearch natively without installing | Documentation for MCP registration |
| docker compose | v2+ | Run infra services separately | Alternative to all-in-one image |

## Architecture Patterns

### Current s6-overlay Service Dependency Chain (Before)

```
s6-overlay /init
    |
    +--> svc-postgresql (longrun, notification-fd readiness)
    |        |
    +--> svc-ollama (longrun, notification-fd readiness)
    |        |
    |        +--> init-warmup (oneshot, depends: svc-ollama)
    |                 |
    +--> svc-mcp (longrun, depends: svc-postgresql, svc-ollama, init-warmup)  <-- REMOVE
             |
             +--> init-ready (oneshot, depends: svc-mcp)  <-- REWIRE
```

### Target s6-overlay Service Dependency Chain (After)

```
s6-overlay /init
    |
    +--> svc-postgresql (longrun, notification-fd readiness)
    |
    +--> svc-ollama (longrun, notification-fd readiness)
    |        |
    |        +--> init-warmup (oneshot, depends: svc-ollama)
    |
    +--> init-ready (oneshot, depends: svc-postgresql, init-warmup)
```

Key change: init-ready previously depended on svc-mcp (which transitively depended on everything). Now init-ready needs explicit dependencies on both svc-postgresql and init-warmup (which transitively includes svc-ollama).

### Pattern: s6-overlay Dependency Wiring

Dependencies between s6-rc services are specified via empty marker files in a `dependencies.d/` subdirectory. A service starts only after all its declared dependencies have reached their ready state.

**To add a dependency:** `touch /etc/s6-overlay/s6-rc.d/serviceA/dependencies.d/serviceB`
**To remove a dependency:** Delete the file from `dependencies.d/`
**To register a service in the user bundle:** `touch /etc/s6-overlay/s6-rc.d/user/contents.d/serviceName`
**To unregister:** Delete the file from `user/contents.d/`

### Pattern: Dockerfile Multi-Stage Removal

When removing a build stage from a multi-stage Dockerfile:
1. Remove the entire `FROM ... AS stage-name` block
2. Remove all `COPY --from=stage-name` lines in later stages
3. Remove all environment variables that reference artifacts from the removed stage
4. Verify no ARG/ENV values reference the removed stage

### Anti-Patterns to Avoid

- **Partial svc-mcp removal:** Deleting the svc-mcp directory but leaving its registration in `user/contents.d/svc-mcp` or its dependency marker in `init-ready/dependencies.d/svc-mcp` will crash the container with s6-rc-compile errors.
- **Keeping Python base image:** Using `python:3.11-slim` when no Python code exists in the image wastes ~80MB and falsely signals that Python is a runtime dependency.
- **Forgetting PostgreSQL PATH updates:** When upgrading from PG 16 to PG 17, the binary path changes from `/usr/lib/postgresql/16/bin` to `/usr/lib/postgresql/17/bin`. This path appears in 5 files (Dockerfile ENV, health-check, svc-postgresql/run, svc-postgresql/finish, svc-postgresql/data/check).

## Don't Hand-Roll

Problems that look simple but have existing patterns:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PostgreSQL readiness check | Custom TCP socket test | `pg_isready -h localhost -U cocosearch -d cocosearch` | Handles auth, protocol versions, error reporting |
| Ollama readiness check | Custom HTTP client | `curl -sf http://localhost:11434/api/tags` | Already proven in current health-check |
| Process supervision | shell background jobs | s6-overlay (already in use) | Signal handling, dependency ordering, graceful shutdown |
| PostgreSQL+pgvector image | Build from source | `pgvector/pgvector:pg17` for docker-compose; apt packages for all-in-one | Maintained, tested, multi-arch |

**Key insight:** This phase is purely subtractive. No new solutions need to be built. Every component that remains (svc-postgresql, svc-ollama, init-warmup, health-check, ready-signal) already works and just needs lines removed or paths updated.

## Common Pitfalls

### Pitfall 1: Orphaned s6 Service References Crash Container

**What goes wrong:** s6-rc-compile runs at container start and validates ALL service definitions. If any file in `dependencies.d/` or `user/contents.d/` references a service directory that does not exist, the container exits immediately with a fatal error.
**Why it happens:** svc-mcp is referenced in 6 separate locations across the rootfs tree. Missing even one creates a dangling reference.
**How to avoid:** Delete ALL 6 files that reference svc-mcp (see complete inventory below). After deletion, verify with `find docker/rootfs -name "*mcp*"` returns nothing.
**Warning signs:** Container exits immediately, s6-overlay logs show "s6-rc-compile: fatal" errors.

### Pitfall 2: PostgreSQL PATH Mismatch After Version Upgrade

**What goes wrong:** PostgreSQL binaries are in version-specific paths (`/usr/lib/postgresql/16/bin` vs `/usr/lib/postgresql/17/bin`). The PATH appears in 5 files. Missing one causes that specific script to fail with "command not found" for pg_isready, initdb, pg_ctl, or postgres.
**Why it happens:** The PATH is hardcoded in each script, not inherited from a central config.
**How to avoid:** Search all files for "postgresql/16" and update every occurrence to "postgresql/17".
**Warning signs:** PostgreSQL service fails to start, health check fails, initdb not found.

### Pitfall 3: init-ready Dependency Chain Broken

**What goes wrong:** init-ready currently depends solely on svc-mcp, which transitively depends on everything else. After removing svc-mcp, init-ready has no dependencies and fires immediately before PostgreSQL and Ollama are ready. The ready-signal prints "container ready" prematurely.
**Why it happens:** The transitive dependency through svc-mcp masked the need for direct dependencies.
**How to avoid:** Add two new dependency files: `init-ready/dependencies.d/svc-postgresql` and `init-ready/dependencies.d/init-warmup`. The init-warmup dependency transitively ensures svc-ollama is ready too.
**Warning signs:** "COCOSEARCH_READY" message appears before PostgreSQL accepts connections.

### Pitfall 4: Health Check Still Checks MCP

**What goes wrong:** The health-check script (lines 20-24) curls `localhost:3000/health`. With no MCP server, this always fails, making Docker report the container as unhealthy.
**Why it happens:** Health check was not updated when svc-mcp was removed.
**How to avoid:** Remove the MCP health check block (lines 20-24). Only check PostgreSQL and Ollama.
**Warning signs:** `docker ps` shows container as "unhealthy" despite services working.

### Pitfall 5: Existing Users' Docker Run Commands Break

**What goes wrong:** Users who followed Option #1 in the README have `docker run -p 3000:3000 cocosearch` commands that expect the MCP server inside the container. After this change, port 3000 is not exposed and no MCP server runs.
**Why it happens:** The deployment model changed from all-in-one to infra-only.
**How to avoid:** Update README to replace Option #1 with the new infra-only model. Document the migration path clearly: use docker-compose for infra + uvx for MCP.

## Code Examples

### Complete File Inventory: What to Delete

These files must be entirely removed from the repository:

```
docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/run              # MCP service run script
docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/type              # Service type (longrun)
docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/init-warmup      # Dep marker
docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/svc-ollama       # Dep marker
docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/svc-postgresql   # Dep marker
docker/rootfs/etc/s6-overlay/s6-rc.d/init-ready/dependencies.d/svc-mcp       # Dep on removed service
docker/rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/svc-mcp                 # Bundle registration
```

Total: 7 files to delete (the svc-mcp directory tree: 5 files + 2 external references).

### Complete File Inventory: What to Modify

#### 1. docker/Dockerfile (major changes)

Remove:
- Lines 22-36: Entire Stage 2 (python-builder)
- Lines 98-99: `COPY --from=python-builder` lines
- Line 102: `/app/.venv/bin` from PATH env
- Line 103: `PYTHONPATH="/app/src"` env
- Lines 122-123: `COCOSEARCH_MCP_PORT`, `COCOSEARCH_MCP_TRANSPORT` env vars
- Line 127: `COCOSEARCH_LOG_LEVEL` env var
- Line 147: Port 3000 from EXPOSE

Change:
- Line 41: Base image from `python:3.11-slim` to `debian:bookworm-slim`
- Lines 82-84: PostgreSQL packages from `postgresql-16`/`postgresql-16-pgvector` to `postgresql-17`/`postgresql-17-pgvector`
- Line 102: PATH from `/usr/lib/postgresql/16/bin` to `/usr/lib/postgresql/17/bin`
- Lines 1-6: Header comments (remove MCP server reference, update run command)
- Lines 43-45: Labels (change to infrastructure-only description)

#### 2. docker/rootfs/etc/s6-overlay/scripts/health-check

Remove lines 20-24 (MCP server health check). Keep PostgreSQL and Ollama checks only.
Update line 6: PATH from `postgresql/16` to `postgresql/17`.

Target content:
```sh
#!/bin/sh
# Combined health check - returns 0 only when infrastructure services are ready
# Used by Docker HEALTHCHECK

export PATH="/usr/lib/postgresql/17/bin:$PATH"

# Check PostgreSQL
if ! pg_isready -h localhost -U cocosearch -d cocosearch > /dev/null 2>&1; then
    echo "PostgreSQL not ready"
    exit 1
fi

# Check Ollama
if ! curl -sf http://localhost:${COCOSEARCH_OLLAMA_PORT:-11434}/api/tags > /dev/null 2>&1; then
    echo "Ollama not ready"
    exit 1
fi

# All services ready
exit 0
```

#### 3. docker/rootfs/etc/s6-overlay/scripts/ready-signal

Remove MCP Server and Transport lines. Update header comment.

Target content:
```sh
#!/bin/sh
# Print ready marker to stdout for scripting integration
# This runs AFTER all infrastructure services are ready

echo "=========================================="
echo "CocoSearch infrastructure ready"
echo "=========================================="
echo "PostgreSQL:  localhost:${COCOSEARCH_PG_PORT:-5432}"
echo "Ollama:      localhost:${COCOSEARCH_OLLAMA_PORT:-11434}"
echo "=========================================="
echo ""
echo "COCOSEARCH_READY"
echo ""
```

#### 4. docker/rootfs/etc/s6-overlay/s6-rc.d/init-ready/dependencies.d/

- Delete: `svc-mcp` (existing file)
- Create: `svc-postgresql` (empty file)
- Create: `init-warmup` (empty file)

This rewires init-ready to depend on both PostgreSQL and Ollama-warmup (which depends on svc-ollama).

#### 5. docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/run

Update line 5: PATH from `postgresql/16` to `postgresql/17`.
Update line 11: `initdb` and all `pg_ctl`/`psql`/`postgres` calls will pick up PG 17 from the PATH.

#### 6. docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/finish

Update line 3: PATH from `postgresql/16` to `postgresql/17`.

#### 7. docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/data/check

Update line 2: PATH from `postgresql/16` to `postgresql/17`.

### PostgreSQL 16 to 17 PATH Update Locations

All 5 locations that need `postgresql/16` changed to `postgresql/17`:

| File | Line | Current |
|------|------|---------|
| `docker/Dockerfile` | 102 | `ENV PATH="/app/.venv/bin:/usr/lib/postgresql/16/bin:$PATH"` |
| `docker/rootfs/etc/s6-overlay/scripts/health-check` | 6 | `export PATH="/usr/lib/postgresql/16/bin:$PATH"` |
| `docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/run` | 5 | `export PATH="/usr/lib/postgresql/16/bin:$PATH"` |
| `docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/finish` | 3 | `export PATH="/usr/lib/postgresql/16/bin:$PATH"` |
| `docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/data/check` | 2 | `export PATH="/usr/lib/postgresql/16/bin:$PATH"` |

Note: The Dockerfile PATH line also removes `/app/.venv/bin` (no longer needed).

### Environment Variables After Simplification

| Variable | Action | Reason |
|----------|--------|--------|
| `COCOSEARCH_PG_PORT` | KEEP | PostgreSQL port configuration |
| `COCOSEARCH_OLLAMA_PORT` | KEEP | Ollama port configuration |
| `COCOSEARCH_EMBED_MODEL` | KEEP | Model pre-bake and warmup |
| `COCOSEARCH_DATABASE_URL` | KEEP | Used by PG init scripts for credential setup |
| `OLLAMA_HOST` | KEEP | Ollama binding configuration |
| `OLLAMA_MODELS` | KEEP | Model storage path |
| `PGDATA` | KEEP | PostgreSQL data directory |
| `HOME` | KEEP | Required by Ollama envconfig |
| `S6_KILL_GRACETIME` | KEEP | s6-overlay shutdown timing |
| `S6_SERVICES_GRACETIME` | KEEP | s6-overlay shutdown timing |
| `COCOSEARCH_MCP_PORT` | REMOVE | No MCP server in container |
| `COCOSEARCH_MCP_TRANSPORT` | REMOVE | No MCP server in container |
| `COCOSEARCH_LOG_LEVEL` | REMOVE | CocoSearch-specific, no app in container |

### Documentation Updates Required

#### README.md (Getting Started section)

Option #1 must be rewritten. Currently describes all-in-one image with MCP server. Should describe infra-only image:
- Build command stays the same: `docker build -t cocosearch -f docker/Dockerfile .`
- Run command changes: expose only 5432 and 11434 (not 3000)
- Add: install CocoSearch natively via `uvx` or `uv pip install`
- Add: register MCP server pointing at Docker services

Option #2 (docker compose) is already correct -- it runs separate containers and CocoSearch natively.

#### docs/mcp-configuration.md

Currently does not reference Docker-specific setup. May benefit from a section explaining that Docker provides infrastructure while MCP registration uses uvx.

#### docker/.dockerignore

May need updates if `pyproject.toml`, `uv.lock`, `README.md`, `src/` are no longer copied into the build context. However, since the model-downloader stage does not need these files and the python-builder stage is removed, the `.dockerignore` can be simplified or left as-is (extra exclusions are harmless).

### New Dockerfile Structure (Target)

```dockerfile
# CocoSearch Infrastructure Docker Image
# Bundles PostgreSQL+pgvector and Ollama with pre-baked nomic-embed-text model
# No application code -- CocoSearch runs natively via uvx
#
# Build: docker build -t cocosearch -f docker/Dockerfile .
# Run:   docker run -v cocosearch-data:/data -p 5432:5432 -p 11434:11434 cocosearch

# Stage 1: Download Ollama model during build
FROM ollama/ollama:latest AS model-downloader
RUN ollama serve & sleep 5 && ollama pull nomic-embed-text && pkill ollama

# Stage 2: Final runtime image (infrastructure only)
FROM debian:bookworm-slim

LABEL org.opencontainers.image.title="CocoSearch Infrastructure"
LABEL org.opencontainers.image.description="PostgreSQL+pgvector and Ollama for CocoSearch"
...

# Install s6-overlay, PostgreSQL 17, pgvector
# Copy Ollama binary
# Copy pre-baked model
# Copy rootfs overlay
# EXPOSE 5432 11434
# HEALTHCHECK (PG + Ollama only)
# ENTRYPOINT ["/init"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All-in-one image (PG+Ollama+App) | Infra-only image (PG+Ollama) + native app | This phase | Smaller image, cleaner separation, uvx for app |
| python:3.11-slim base | debian:bookworm-slim base | This phase | ~80MB savings, clearer intent |
| PostgreSQL 16 in Dockerfile | PostgreSQL 17 (aligned with docker-compose) | This phase | Consistency across deployment methods |
| `svc-mcp` s6 service | Removed entirely | This phase | Simpler s6 service tree |

**Deprecated/outdated after this phase:**
- Docker Option #1 "all-in-one" references in README
- Port 3000 in any Docker-related documentation
- `python-builder` stage references
- `COCOSEARCH_MCP_PORT`, `COCOSEARCH_MCP_TRANSPORT`, `COCOSEARCH_LOG_LEVEL` env vars in Docker context

## Open Questions

Things that could not be fully resolved:

1. **Existing users' pg_data migration from PG 16 to PG 17**
   - What we know: Upgrading PostgreSQL major version requires data directory reinitialization or pg_upgrade
   - What is unclear: Whether any users have persistent data in the all-in-one image worth preserving
   - Recommendation: Document that users should delete their data volume (`docker volume rm cocosearch-data`) when upgrading. This is an infra-only image; the real data comes from re-indexing.

2. **s6-overlay version: keep 3.2.2.0 or update?**
   - What we know: Current Dockerfile uses 3.2.2.0. Latest release is 3.2.1.0 (May 2025), which is actually older. The 3.2.2.0 may be a pre-release or custom version.
   - What is unclear: Whether 3.2.2.0 is correct (it appears the versioning may be non-sequential)
   - Recommendation: Keep the current version as-is; this phase is about simplification, not upgrading dependencies.

3. **Should init-ready be kept or removed entirely?**
   - What we know: init-ready exists to fire the ready-signal script after all services start. It is useful for logging but not functionally necessary.
   - What is unclear: Whether any automation depends on the "COCOSEARCH_READY" output
   - Recommendation: Keep init-ready and rewire it. It provides a useful startup confirmation log message and costs nothing.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** - Direct reading of `docker/Dockerfile`, all 27 files in `docker/rootfs/`, `docker-compose.yml`, `README.md`, `docs/mcp-configuration.md`, `dev-setup.sh`, `.env.example`, `pyproject.toml`
- **Prior milestone research** - `.planning/research/ARCHITECTURE-v1.10-integration.md` (comprehensive Docker stripping analysis, verified against codebase)
- **Prior milestone research** - `.planning/research/STACK.md` (Docker simplification section with file inventories)
- **Prior milestone research** - `.planning/research/PITFALLS-v1.10.md` (Pitfall 1: Docker stripping, Pitfall 11: orphaned s6 references)
- **Phase 43 verification** - `.planning/phases/43-bug-fix-credential-defaults/43-VERIFICATION.md` (confirms credentials aligned to cocosearch:cocosearch)

### Secondary (MEDIUM confidence)
- [s6-overlay GitHub repository](https://github.com/just-containers/s6-overlay) - Dependencies.d mechanism, bundle registration via contents.d
- [PostgreSQL APT Repository](https://packages.debian.org/search?keywords=postgresql-17-pgvector) - postgresql-17-pgvector availability for Debian bookworm
- [How to understand S6 Overlay v3](https://darkghosthunter.medium.com/how-to-understand-s6-overlay-v3-95c81c04f075) - Service types and dependency wiring
- [uv tools documentation](https://docs.astral.sh/uv/guides/tools/) - uvx (uv tool run) for running CocoSearch without installing

### Tertiary (LOW confidence)
- [The best Docker base image for Python (Feb 2026)](https://pythonspeed.com/articles/base-image-python-docker-images/) - python:3.11-slim is based on debian:bookworm-slim, confirms ~80MB overhead estimate

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Direct analysis of existing codebase plus prior verified research
- Architecture: HIGH - Complete file inventory built by reading every file in docker/rootfs/
- Pitfalls: HIGH - Enumerated from prior milestone research and verified against codebase
- Documentation updates: HIGH - Read all docs that mention Docker

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable domain; s6-overlay and Dockerfile patterns change slowly)
