---
phase: 44-docker-image-simplification
plan: 01
subsystem: docker
tags: [docker, dockerfile, s6-overlay, postgresql, infrastructure]

dependency-graph:
  requires: []
  provides:
    - infrastructure-only Docker image (no Python, no MCP)
    - PostgreSQL 17 with pgvector
    - debian:bookworm-slim base image
  affects:
    - Any future Docker image changes
    - docker-compose.yml (already aligned with PG 17)

tech-stack:
  added: []
  removed:
    - python:3.11-slim (base image)
    - uv (Python package manager in builder stage)
  patterns:
    - Infrastructure-only Docker image (app runs natively via uvx)

file-tracking:
  key-files:
    created: []
    modified:
      - docker/Dockerfile
      - docker/.dockerignore
      - docker/rootfs/etc/s6-overlay/scripts/health-check
      - docker/rootfs/etc/s6-overlay/scripts/ready-signal
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/run
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/finish
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-postgresql/data/check
    deleted:
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/run
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/type
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/init-warmup
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/svc-ollama
      - docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/svc-postgresql
      - docker/rootfs/etc/s6-overlay/s6-rc.d/init-ready/dependencies.d/svc-mcp
      - docker/rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/svc-mcp

decisions:
  - id: base-image-bookworm
    decision: "Switch base image from python:3.11-slim to debian:bookworm-slim"
    rationale: "No Python needed in container; saves ~80MB; clearer infrastructure intent"
  - id: pg-17-upgrade
    decision: "Upgrade PostgreSQL from 16 to 17"
    rationale: "Aligns with docker-compose.yml which already uses pg17"

metrics:
  duration: "~2 minutes"
  completed: 2026-02-08
---

# Phase 44 Plan 01: Docker Image Simplification Summary

Infrastructure-only Docker image with debian:bookworm-slim base, PG17+pgvector, Ollama; all Python/MCP code stripped.

## What Was Done

### Task 1: Rewrite Dockerfile to infrastructure-only
**Commit:** `1269b3f`

Rewrote the Dockerfile from a 3-stage build (model-downloader, python-builder, runtime) to a 2-stage build (model-downloader, runtime). Key changes:

- Removed entire Python builder stage (Stage 2)
- Changed base image from `python:3.11-slim` to `debian:bookworm-slim`
- Removed `COPY --from=python-builder` lines
- Removed `/app/.venv/bin` from PATH, `PYTHONPATH`, MCP env vars (`COCOSEARCH_MCP_PORT`, `COCOSEARCH_MCP_TRANSPORT`, `COCOSEARCH_LOG_LEVEL`)
- Removed `git` from apt-get install (only needed for Python package builds)
- Removed `/mnt/repos` from directory structure
- Upgraded PostgreSQL packages from 16 to 17
- Updated PATH to `/usr/lib/postgresql/17/bin:$PATH`
- Removed port 3000 from EXPOSE (now only `5432 11434`)
- Updated labels to "CocoSearch Infrastructure"
- Simplified `.dockerignore` to remove Python-specific exclusions and `!README.md` exception

### Task 2: Remove svc-mcp, rewire init-ready, update scripts and PG paths
**Commit:** `c39192f`

Deleted the entire svc-mcp service and all references, rewired the s6-overlay dependency graph, and updated PostgreSQL paths:

- Deleted 5 files in `svc-mcp/` directory tree (run, type, 3 dependency markers)
- Deleted `init-ready/dependencies.d/svc-mcp` and `user/contents.d/svc-mcp`
- Created `init-ready/dependencies.d/svc-postgresql` and `init-ready/dependencies.d/init-warmup` marker files
- Updated health-check script: removed MCP health check block, updated PG path to 17, updated comment to "infrastructure services"
- Updated ready-signal script: removed MCP Server and Transport lines, updated description to "infrastructure services"
- Updated PostgreSQL PATH from 16 to 17 in `svc-postgresql/run`, `svc-postgresql/finish`, `svc-postgresql/data/check`

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| debian:bookworm-slim base image | No Python needed; saves ~80MB; clearer infrastructure intent |
| PostgreSQL 16 to 17 upgrade | Aligns with docker-compose.yml which already uses pg17 |

## Verification Results

All verification checks passed:

1. Zero `python-builder` references in Dockerfile
2. Zero `mcp` references anywhere in `docker/rootfs/`
3. Zero `postgresql/16` references anywhere in `docker/`
4. EXPOSE shows `5432 11434` only (no 3000)
5. No `*mcp*` files found in rootfs
6. init-ready dependencies: `init-warmup` and `svc-postgresql` only
7. `debian:bookworm-slim` confirmed as base image

## Next Phase Readiness

The Docker image is now infrastructure-only. No blockers for subsequent phases. The image provides PostgreSQL 17 + pgvector and Ollama with pre-baked nomic-embed-text model. CocoSearch application runs natively via `uvx`.
