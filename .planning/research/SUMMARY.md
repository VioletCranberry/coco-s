# Project Research Summary

**Project:** CocoSearch v1.6 All-in-One Docker Deployment
**Domain:** Containerized MCP Server with Embedded Infrastructure
**Researched:** 2026-02-01
**Confidence:** HIGH

## Executive Summary

CocoSearch v1.6 aims to deliver a single `docker run` experience that bundles PostgreSQL (with pgvector), Ollama (with nomic-embed-text), and the MCP server into one container. Research confirms this pattern is well-established in the ecosystem (e.g., Open WebUI's ollama bundle) and achievable with the existing codebase architecture. The key additions are: (1) s6-overlay for process supervision, (2) Streamable HTTP transport for MCP (SSE is deprecated), and (3) entrypoint-based model pulling until Ollama's `--local` flag ships.

The recommended approach prioritizes correctness over optimization. Use s6-overlay (not supervisord) because it properly handles PID 1 and service dependencies. Use Streamable HTTP transport (not SSE) because SSE is officially deprecated in the MCP spec as of 2025-03-26. Pull the embedding model at container startup rather than baking it into the image to keep the image under 750MB.

Key risks center on container lifecycle: improper PID 1 handling causes PostgreSQL data corruption on restart; stdout pollution in stdio mode corrupts the MCP protocol; and race conditions in service startup cause intermittent failures. All three risks have straightforward mitigations through proper init system usage, stderr-only logging, and explicit startup sequencing.

## Key Findings

### Recommended Stack

The existing stack requires minimal additions. The Python dependencies (`mcp[cli]>=1.26.0`, `cocoindex`, `psycopg`) already support everything needed. New additions are container-level infrastructure.

**Core technologies:**
- **s6-overlay 3.2.2.0:** Process supervision in container. Properly handles PID 1, service dependencies, and container exit on failure. Superior to supervisord for container use cases.
- **Streamable HTTP transport:** Modern MCP transport replacing deprecated SSE. Already supported in current mcp[cli] version via FastMCP's `transport="streamable-http"`.
- **nomic-embed-text (274MB):** Embedding model pulled at container startup. Pre-baking into image is optional optimization for air-gapped environments.

**What NOT to add:**
- supervisord (doesn't reflect child health to orchestrators)
- SSE transport (deprecated, but support via mcp-remote proxy for legacy clients)
- nginx/caddy (FastMCP handles HTTP internally)
- Model baking in initial version (adds 300MB to image, complicates build)

### Expected Features

**Must have (table stakes):**
- Single `docker run` command with all services bundled
- Pre-pulled embedding model (no download delay after container ready)
- Volume mount for codebases (`-v /local/repo:/mnt/repos`)
- Optional persistence volume for PostgreSQL and Ollama data
- Health check endpoint for container orchestration
- Service startup ordering (PostgreSQL -> Ollama -> MCP)
- Graceful shutdown on SIGTERM
- stdio transport support (existing, for Claude Code)
- HTTP transport support (Streamable HTTP for remote access)
- Container logging to stdout/stderr

**Should have (competitive):**
- GPU passthrough documentation (`--gpus=all` for faster embeddings)
- Multi-arch images (linux/amd64 and linux/arm64)
- Reasonable image size (<750MB without baked model)
- Distinct readiness vs liveness endpoints

**Defer to v1.7+:**
- Init-time auto-indexing of mounted directories
- Progress/status API for long operations
- Docker MCP Toolkit catalog submission

### Architecture Approach

The all-in-one container runs three services under s6-overlay supervision. Each service is a "longrun" type with explicit dependencies. Model pulling is a "oneshot" that gates MCP server startup. The existing codebase needs only one change: `server.py` must accept a transport parameter (default: stdio, option: streamable-http).

**Major components:**
1. **PostgreSQL service** — Starts first, waits for pg_isready before dependents start
2. **Ollama service** — Starts after base init, model-pull oneshot depends on it
3. **model-pull oneshot** — Ensures nomic-embed-text is available before MCP starts
4. **cocosearch service** — MCP server, depends on both postgres and model-pull

**Service dependency chain:**
```
base (system init)
  |-- postgres (longrun) ----------------------+
  +-- ollama (longrun)                         |
        +-- model-pull (oneshot) --------------+--> cocosearch (longrun)
```

**Claude Desktop integration:**
- Claude Pro/Max/Team: Direct HTTP via Settings > Integrations
- Claude Free: Use `mcp-remote` npm package as bridge to HTTP endpoint
- Alternative: `docker exec -i container cocosearch mcp` for stdio access

### Critical Pitfalls

1. **PID 1 signal handling (CRITICAL)** — Use s6-overlay or tini as PID 1. Bash scripts ignore SIGTERM, causing PostgreSQL data corruption on `docker stop`. Test: `time docker stop container` should complete in <10s.

2. **stdout pollution in stdio mode (CRITICAL)** — Any logging to stdout corrupts JSON-RPC stream. Keep all logging on stderr. Audit dependencies for stdout usage. Test: capture stdout during MCP operation, verify only valid JSON.

3. **PostgreSQL init scripts skipped (CRITICAL)** — Init scripts only run on empty data dir. Implement app-level schema management or startup check: `CREATE EXTENSION IF NOT EXISTS vector`.

4. **Ollama cold start blocks application (CRITICAL)** — Container appears healthy before model loads. Pull model in entrypoint before marking ready. Healthcheck must verify model presence, not just Ollama server.

5. **Service startup race conditions (MODERATE)** — Use s6-overlay's dependency system. Do not start cocosearch until pg_isready passes AND model-pull completes.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Container Foundation
**Rationale:** Process supervision, signal handling, and startup sequencing must be correct before adding any application code. Getting PID 1 wrong causes data corruption.
**Delivers:** Working multi-service container with PostgreSQL + Ollama + placeholder app
**Addresses:** Health check endpoint, service startup ordering, graceful shutdown
**Avoids:** PID 1 signal handling pitfall, service race conditions, PostgreSQL init issues

### Phase 2: MCP Transport Integration
**Rationale:** Transport is the interface between container and Claude clients. Must work before user experience can be validated.
**Delivers:** Working MCP server with stdio + HTTP transport selection
**Uses:** Existing mcp[cli], FastMCP transport options
**Implements:** Transport layer in server.py, environment-based transport selection
**Avoids:** stdout pollution, dual transport maintenance burden

### Phase 3: Model and Data Management
**Rationale:** With container and transport working, focus on the embedding model lifecycle and data persistence.
**Delivers:** Entrypoint model pulling, data volume persistence, healthcheck improvements
**Addresses:** Pre-pulled embedding model, optional persistence volume
**Avoids:** Cold start blocking, image bloat from baked models

### Phase 4: User Experience and Documentation
**Rationale:** Final phase polishes the experience and documents usage patterns.
**Delivers:** Claude Desktop/Code configuration examples, docker run examples, troubleshooting guide
**Addresses:** Documentation for MCP client setup, GPU passthrough docs
**Avoids:** Working directory confusion (document PROJECT_ROOT env var pattern)

### Phase Ordering Rationale

- **Foundation before features:** Container lifecycle (Phase 1) determines whether data survives restarts. Must be correct before adding complexity.
- **Transport before model:** Transport is how users interact with the container. Model management is invisible to users.
- **Code before docs:** Documentation should describe working behavior, not aspirational features.
- **Dependencies discovered:** PostgreSQL must start before MCP (database connection). Ollama must have model before MCP (embeddings). s6-overlay enforces this ordering.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Transport):** Streamable HTTP adoption by Claude Desktop is uncertain. May need to also support legacy SSE via mcp-remote bridge initially.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Container):** s6-overlay documentation is comprehensive. PostgreSQL + Ollama container patterns are well-established.
- **Phase 3 (Model):** Ollama model pulling is straightforward. No unknowns.
- **Phase 4 (Docs):** Documentation phase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | s6-overlay verified on GitHub, mcp transport verified in FastMCP docs |
| Features | HIGH | Docker MCP patterns well-documented by Docker Inc. blog posts |
| Architecture | HIGH | Verified against existing codebase; minimal changes needed |
| Pitfalls | HIGH | Sources include official docs, GitHub issues, and known failure modes |

**Overall confidence:** HIGH

### Gaps to Address

- **Streamable HTTP client support:** Need to verify which Claude Desktop versions support Streamable HTTP directly vs requiring mcp-remote bridge. Monitor MCP ecosystem during implementation.
- **Multi-arch build:** Research suggests `docker buildx` for arm64 support, but not deeply explored. Address during Phase 4 if needed.
- **Model pre-baking optimization:** Documented as possible but deferred. If users request faster cold starts, can add in v1.7.

## Sources

### Primary (HIGH confidence)
- [s6-overlay GitHub releases](https://github.com/just-containers/s6-overlay) — version 3.2.2.0, installation, service definitions
- [FastMCP Running Server](https://gofastmcp.com/deployment/running-server) — transport options, SSE deprecation notice
- [MCP Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) — official transport specification
- [Docker Multi-Process Containers](https://docs.docker.com/engine/containers/multi-service_container/) — official supervisord/multi-service docs
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres/) — init script behavior, data directory semantics
- [Ollama Docker Hub](https://hub.docker.com/r/ollama/ollama) — container deployment patterns
- [tini GitHub](https://github.com/krallin/tini) — PID 1 handling

### Secondary (MEDIUM confidence)
- [DoltHub: Pull-first Ollama](https://www.dolthub.com/blog/2025-03-19-a-pull-first-ollama-docker-image/) — model pulling workaround
- [Docker Build to Prod MCP Servers](https://www.docker.com/blog/build-to-prod-mcp-servers-with-docker/) — container best practices
- [Ollama GitHub #6006](https://github.com/ollama/ollama/issues/6006) — cold start documentation

### Tertiary (LOW confidence)
- Ollama `--local` flag status — not yet released per research, monitor releases

---
*Research completed: 2026-02-01*
*Ready for roadmap: yes*
