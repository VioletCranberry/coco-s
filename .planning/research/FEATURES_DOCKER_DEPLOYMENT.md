# Feature Landscape: All-in-One Docker Deployment for MCP Server (v1.6)

**Domain:** All-in-one Docker container bundling MCP server with embedded dependencies (Ollama, PostgreSQL)
**Researched:** 2026-02-01
**Existing Context:** CocoSearch v1.5 with stdio MCP server, Docker Compose for dev setup
**Confidence:** HIGH (verified against Docker docs, MCP specification, Ollama Docker image)

## Executive Summary

All-in-one Docker deployments for MCP servers follow established patterns from the broader container ecosystem. The key insight is that "single `docker run` command" is the primary value proposition, distinguishing it from multi-container Docker Compose setups. Users expect the container to be immediately usable without additional setup steps like downloading models or configuring databases.

The MCP transport landscape is in flux: stdio works for local CLI agents (Claude Code), SSE is deprecated but still used by Claude Desktop, and Streamable HTTP is the future standard. A production-ready deployment must support at least stdio and SSE to cover the primary use cases.

## Table Stakes

Features users expect from an all-in-one Docker MCP deployment. Missing any of these makes the product feel incomplete or broken.

### Container Deployment

| Feature | Why Expected | Complexity | Existing Dependency | Notes |
|---------|--------------|------------|---------------------|-------|
| Single `docker run` command | Core value proposition - "just works" deployment without compose files | Medium | None | Must work: `docker run -v /repos:/mnt ghcr.io/user/cocosearch` |
| Pre-pulled embedding model | Users expect instant startup, not 274MB model download at runtime | Low | Ollama service | nomic-embed-text baked into image during build |
| Volume mount for codebases | Users need to index their local repositories | Low | Indexer | Standard pattern: `-v /local/repo:/mnt/repos` |
| Optional persistence volume | Data survives container restarts without re-indexing | Low | PostgreSQL, Ollama | `-v cocosearch-data:/data` for combined data |
| Environment variable configuration | Standard Docker pattern for runtime settings | Low | Config system | COCOSEARCH_* vars already exist, just document |
| stdout/stderr logging | Users expect `docker logs cocosearch` to show useful output | Low | Logging config | All services must log to container stdout/stderr |

### Service Orchestration

| Feature | Why Expected | Complexity | Existing Dependency | Notes |
|---------|--------------|------------|---------------------|-------|
| Health check endpoint | Container orchestration needs liveness signal for `docker run --wait` | Low | None | HTTP `/health` returning 200 when all services ready |
| Service startup ordering | PostgreSQL and Ollama must be ready before MCP accepts connections | Medium | None | Entrypoint script or supervisord manages sequence |
| Graceful shutdown | Clean database disconnect on SIGTERM, no data corruption | Medium | PostgreSQL connection | PID 1 signal handling with tini or supervisord |
| Process supervision | All three services (PostgreSQL, Ollama, MCP) must restart on crash | Medium | None | Supervisord recommended for multi-process containers |

### MCP Transport

| Feature | Why Expected | Complexity | Existing Dependency | Notes |
|---------|--------------|------------|---------------------|-------|
| stdio transport for Claude Code | Claude Code requires stdio for local MCP servers | Low | Existing MCP server | Already implemented in v1.5, verify works in container |
| SSE transport for Claude Desktop | Claude Desktop uses HTTP-based MCP, SSE still common | Medium | FastMCP | FastMCP supports SSE via `transport="sse"` |
| Documentation for MCP client setup | Users need Claude Desktop/Code configuration examples | Low | Existing docs | JSON config snippets for both transports |

### Operational

| Feature | Why Expected | Complexity | Existing Dependency | Notes |
|---------|--------------|------------|---------------------|-------|
| Container works without GPU | Most developers don't have NVIDIA GPUs | Low | Ollama | CPU mode is Ollama default |
| Reasonable startup time | Container should be ready in < 60 seconds on typical hardware | Low | Service init | PostgreSQL ~5s, Ollama ~10s, model already loaded |
| Clear error messages | When services fail, users need actionable error messages | Low | Logging | Log service startup failures to stderr |


## Differentiators

Features that would set CocoSearch's Docker deployment apart. Not strictly expected, but provide competitive advantage.

### Enhanced Deployment Options

| Feature | Value Proposition | Complexity | Existing Dependency | Notes |
|---------|-------------------|------------|---------------------|-------|
| GPU passthrough support | 10x faster embeddings for large codebases | Low | Ollama | Just document `--gpus=all` flag requirement |
| Readiness endpoint distinct from liveness | Better orchestration: `/ready` checks all services, `/health` checks process alive | Low | None | Useful for kubernetes-style deployments |
| Pre-built multi-arch images | Works on Mac ARM (M1/M2/M3) and Linux x86 without emulation | Medium | Build system | `docker buildx` for linux/amd64, linux/arm64 |
| Container size optimization | Faster pulls, lower storage requirements | Medium | Build system | Multi-stage build, minimal runtime dependencies |

### Enhanced User Experience

| Feature | Value Proposition | Complexity | Existing Dependency | Notes |
|---------|-------------------|------------|---------------------|-------|
| Init-time auto-indexing | Auto-index mounted codebase on first run | Medium | Indexer, config | Detect `/mnt/repos/*` directories, create indexes |
| Progress/status API | Query indexing status during long operations | High | Indexer | WebSocket or polling endpoint for progress |
| Streamable HTTP transport | Modern MCP transport, future-proof for Claude updates | Medium | FastMCP update | Replacing deprecated SSE transport |
| Configuration file mount | Mount custom cocosearch.yaml for advanced configuration | Low | Config loader | `-v ./config.yaml:/etc/cocosearch/config.yaml` |

### Ecosystem Integration

| Feature | Value Proposition | Complexity | Existing Dependency | Notes |
|---------|-------------------|------------|---------------------|-------|
| Docker MCP Toolkit compatibility | Integration with Docker's MCP catalog and ecosystem | Low | None | Proper image metadata, catalog submission |
| Secrets mount support | Secure handling of API keys if external services added later | Low | None | `/run/secrets` pattern, not env vars for secrets |
| Compose file as alternative | Power users get isolated services with compose | Low | Existing compose | Already exists, just document as alternative |


## Anti-Features

Features to deliberately NOT build. Common mistakes or scope creep in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Web UI dashboard | Scope creep - MCP clients are the UI, not the server | Keep CLI and MCP-only interface |
| Runtime model downloading | Slow startup, unreliable networks, breaks offline use | Pre-pull model into image layer during build |
| Multiple embedding models | Image bloat (274MB+ per model), confusing options | Single model (nomic-embed-text), document customization for power users |
| Auto-reindex on file changes | Resource consumption, unpredictable behavior, inotify complexity | Manual index trigger via MCP tool - existing behavior |
| Docker-in-Docker | Security nightmare, complexity for edge case of runtime model pulling | Pre-bake models or use volume mounts for custom models |
| Cloud storage backends | Violates local-first principle | PostgreSQL local storage only |
| Authentication/authorization | Overkill for local-first tool, adds configuration burden | Trust container network isolation |
| Load balancing / clustering | Not needed for single-user local tool | Single-container deployment only |
| Kubernetes manifests | Scope creep beyond target audience | Document "use existing compose file for k8s" |
| Windows container support | Tiny user base, massive complexity | Linux containers only (works on Docker Desktop for Windows) |
| Custom PostgreSQL extensions | Maintenance burden, pgvector is sufficient | Standard pgvector/pgvector image only |
| Embedded monitoring (Prometheus/Grafana) | Out of scope for dev tool, users can add externally | Log to stdout, let users configure external monitoring |


## Feature Dependencies

```
[Image Build Time]
Pre-pulled nomic-embed-text model ─────┐
                                       │
PostgreSQL + pgvector base ────────────┼──> Single docker run command
                                       │
Python environment + cocosearch ───────┘

[Container Runtime - Startup]
                              ┌──> Health check endpoint
                              │
PostgreSQL ready check ───────┼──> Ollama ready check ──> MCP server start
                              │
                              └──> Logging to stdout/stderr

[MCP Transport Layer]
stdio transport (existing) ───────┬──> Claude Code support
                                  │
SSE transport (new) ──────────────┴──> Claude Desktop support

[Data Persistence]
Volume mount for repos ───────────┬──> Codebase access
                                  │
Optional data volume ─────────────┴──> PostgreSQL + Ollama data survival
```


## Transport Protocol Specification

Based on MCP specification research, the transport strategy should be:

### Protocol Comparison

| Protocol | Status | Client Support | Use Case | CocoSearch Support |
|----------|--------|----------------|----------|-------------------|
| stdio | Stable | Claude Code, CLI agents | Local process communication | Already implemented |
| SSE | Deprecated | Claude Desktop (current) | Remote HTTP connections | Must add for v1.6 |
| Streamable HTTP | Current standard | Claude Desktop (future) | Remote HTTP connections | Consider for v1.7 |

### stdio Transport (Existing)

**How it works:** MCP server reads JSON-RPC messages from stdin, writes responses to stdout. The calling process (Claude Code) spawns the server as a subprocess.

**Docker usage pattern:**
```bash
# Claude Code configuration for stdio
docker run -i --rm -v /repos:/mnt ghcr.io/user/cocosearch:latest
```

**Key requirement:** Container must be run with `-i` (interactive) to attach stdin. The `-t` flag should NOT be used as it interferes with JSON-RPC.

### SSE Transport (New for v1.6)

**How it works:** MCP server exposes HTTP endpoint. Client connects via Server-Sent Events for streaming responses.

**Docker usage pattern:**
```bash
# Run container with SSE transport exposed
docker run -d -p 8080:8080 -v /repos:/mnt ghcr.io/user/cocosearch:latest --transport sse

# Claude Desktop connects to http://localhost:8080/sse
```

**Implementation notes:**
- FastMCP supports SSE via `mcp.run(transport="sse")`
- Default port should be 8080 (standard HTTP alternative port)
- Need to expose both `/sse` endpoint and health check
- SSE is deprecated but still needed for Claude Desktop compatibility

### Transport Selection

The container should support both transports via command-line argument or environment variable:

```bash
# stdio (default, for Claude Code)
docker run -i --rm ghcr.io/user/cocosearch:latest

# SSE (for Claude Desktop)
docker run -d -p 8080:8080 ghcr.io/user/cocosearch:latest --transport sse
# or
docker run -d -p 8080:8080 -e MCP_TRANSPORT=sse ghcr.io/user/cocosearch:latest
```


## Container Architecture Specification

### Single Container vs Multi-Container Decision

| Approach | Pros | Cons |
|----------|------|------|
| Single container (supervisord) | Single `docker run`, simpler UX, matches user expectation | Violates "one process per container", harder debugging |
| Docker Compose (3 containers) | Best practice separation, easier debugging | Requires compose file, more complex for users |

**Recommendation:** Single container with supervisord for all-in-one image.

**Rationale:**
1. Target UX is literally `docker run <image>` with minimal flags
2. Open WebUI successfully uses single-container pattern for Ollama+WebUI bundle
3. PostgreSQL, Ollama, and Python MCP server are all stable, well-understood services
4. Debugging is acceptable with proper logging configuration
5. Existing docker-compose.yml remains available for users who prefer separation

### Supervisord Configuration Structure

```ini
[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0

[program:postgresql]
command=/usr/lib/postgresql/17/bin/postgres -D /data/postgres
priority=10
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
autorestart=true

[program:ollama]
command=/usr/local/bin/ollama serve
priority=20
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
autorestart=true

[program:cocosearch]
command=/app/entrypoint.sh
priority=30
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
autorestart=true
```

**Priority ordering:** PostgreSQL (10) starts first, Ollama (20) second, CocoSearch MCP (30) last.

### Entrypoint Script Flow

```bash
#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
until pg_isready -h localhost -p 5432; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Wait for Ollama to be ready
until curl -s http://localhost:11434/api/tags > /dev/null; do
  echo "Waiting for Ollama..."
  sleep 2
done

# Verify model is available (should be pre-pulled)
if ! ollama list | grep -q nomic-embed-text; then
  echo "ERROR: nomic-embed-text model not found. Image may be corrupted."
  exit 1
fi

# Set environment variables for CocoSearch
export COCOSEARCH_DATABASE_URL="postgresql://cocosearch:cocosearch@localhost:5432/cocosearch"
export COCOSEARCH_OLLAMA_URL="http://localhost:11434"

# Run MCP server with configured transport
exec cocosearch mcp --transport "${MCP_TRANSPORT:-stdio}"
```

### Health Check Implementation

```bash
# /health endpoint handler or script
#!/bin/bash

# Check PostgreSQL
pg_isready -h localhost -p 5432 -q || exit 1

# Check Ollama
curl -sf http://localhost:11434/api/tags > /dev/null || exit 1

# Check CocoSearch MCP process
pgrep -f "cocosearch mcp" > /dev/null || exit 1

exit 0
```

**Dockerfile HEALTHCHECK:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD /app/healthcheck.sh
```


## Volume Mount Specification

### Required Mounts

| Mount Point | Purpose | Example |
|-------------|---------|---------|
| `/mnt/repos` | Codebase directories to index | `-v /home/user/projects:/mnt/repos:ro` |

**Read-only mount recommended:** Codebases should be mounted `:ro` (read-only) since CocoSearch only reads files for indexing.

### Optional Mounts

| Mount Point | Purpose | Example |
|-------------|---------|---------|
| `/data` | Persistent storage for PostgreSQL and Ollama | `-v cocosearch-data:/data` |
| `/etc/cocosearch/config.yaml` | Custom configuration file | `-v ./config.yaml:/etc/cocosearch/config.yaml:ro` |

### Data Directory Structure

```
/data/
├── postgres/          # PostgreSQL data directory
│   └── ...
└── ollama/            # Ollama models and cache
    └── .ollama/
        └── models/
            └── nomic-embed-text/
```


## MVP Recommendation for v1.6

### Must Ship (Table Stakes)

1. **Single `docker run` command** with all services bundled
2. **Pre-pulled nomic-embed-text model** in image (no runtime download)
3. **Volume mount support** for codebases (`-v /local/repo:/mnt/repos`)
4. **Optional persistence volume** for PostgreSQL and Ollama data
5. **Health check endpoint** for container orchestration
6. **Service startup ordering** (PostgreSQL -> Ollama -> MCP server)
7. **Graceful shutdown** on SIGTERM
8. **stdio transport** (existing, verify works in container)
9. **SSE transport** for Claude Desktop (new)
10. **Container logging** to stdout/stderr (`docker logs` works)
11. **Documentation** for both Claude Code and Claude Desktop setup

### Should Ship (High Value)

12. **GPU passthrough documentation** (just docs, `--gpus=all` flag)
13. **Multi-arch images** (linux/amd64 and linux/arm64)
14. **Reasonable image size** (multi-stage build to minimize)

### Defer to v1.7+

15. **Streamable HTTP transport** - Wait for Claude Desktop adoption clarity
16. **Init-time auto-indexing** - Complexity vs value, users can call index tool
17. **Progress/status API** - High complexity, low immediate value
18. **Docker MCP Toolkit catalog submission** - After deployment stabilizes


## Expected User Experience

### Claude Code Setup

```json
// ~/.claude/mcp_servers.json (or project .mcp.json)
{
  "mcpServers": {
    "cocosearch": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/home/user/projects:/mnt/repos:ro",
        "-v", "cocosearch-data:/data",
        "ghcr.io/user/cocosearch:latest"
      ]
    }
  }
}
```

### Claude Desktop Setup

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "cocosearch": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

With container running:
```bash
docker run -d --name cocosearch \
  -p 8080:8080 \
  -v /home/user/projects:/mnt/repos:ro \
  -v cocosearch-data:/data \
  ghcr.io/user/cocosearch:latest --transport sse
```

### Quick Start Flow

```bash
# 1. Pull and run (data persists across restarts)
docker run -d --name cocosearch \
  -p 8080:8080 \
  -v ~/projects:/mnt/repos:ro \
  -v cocosearch-data:/data \
  ghcr.io/user/cocosearch:latest --transport sse

# 2. Verify health
curl http://localhost:8080/health

# 3. Configure Claude Desktop (one-time)
# Add URL to claude_desktop_config.json

# 4. In Claude Desktop, use MCP tools:
# - index_codebase(path="/mnt/repos/myproject", index_name="myproject")
# - search_code(query="authentication logic", index_name="myproject")
```


## Sources

### Docker MCP Best Practices
- [Docker: Build to Prod MCP Servers](https://www.docker.com/blog/build-to-prod-mcp-servers-with-docker/) - Container isolation, security defaults
- [Docker: MCP Server Best Practices](https://www.docker.com/blog/mcp-server-best-practices/) - Tool naming, error handling patterns
- [Docker: MCP Toolkit](https://www.docker.com/blog/mcp-toolkit-mcp-servers-that-just-work/) - Secure defaults, credential handling
- [Docker: Connect MCP to Claude Desktop](https://www.docker.com/blog/connect-mcp-servers-to-claude-desktop-with-mcp-toolkit/) - SSE transport configuration

### MCP Transport Protocols
- [MCP Specification: Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) - Official transport specification (stdio, SSE, Streamable HTTP)
- [MCP Transport Comparison](https://mcpcat.io/guides/comparing-stdio-sse-streamablehttp/) - When to use each transport
- [Roo Code: MCP Server Transports](https://docs.roocode.com/features/mcp/server-transports) - Practical transport selection guide
- [Cloudflare: MCP Transport](https://developers.cloudflare.com/agents/model-context-protocol/transport/) - HTTP transport implementation

### All-in-One Container Patterns
- [Open WebUI Ollama Bundle](https://docs.openwebui.com/) - Single container pattern: `ghcr.io/open-webui/open-webui:ollama`
- [Ollama + PostgreSQL Stack](https://blog.revold.us/easily-install-ollama-openwebui-postgresql-pgvector/) - Docker Compose multi-service pattern
- [Docker Multi-Service Containers](https://docs.docker.com/engine/containers/multi-service_container/) - Official supervisord documentation

### Container Health and Lifecycle
- [Docker Compose Health Checks](https://last9.io/blog/docker-compose-health-checks/) - Health check best practices
- [Docker Graceful Shutdown](https://oneuptime.com/blog/post/2026-01-16-docker-graceful-shutdown-signals/view) - SIGTERM handling, PID 1 considerations
- [Supervisord in Docker](https://dzone.com/articles/running-multiple-services-inside-a-single-containe) - Multi-process container management
- [Docker Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) - Service dependency handling

### Service-Specific Documentation
- [Ollama Docker](https://docs.ollama.com/docker) - Official Ollama container documentation
- [Ollama Health Check](https://github.com/ollama/ollama/issues/1378) - `/api/tags` endpoint for health checks
- [PostgreSQL pgvector Docker](https://dev.to/ninjasoards/setup-postgresql-w-pgvector-in-a-docker-container-4ghe) - `pg_isready` health checks
- [pgvector Docker Hub](https://hub.docker.com/r/pgvector/pgvector) - Official pgvector image

### GPU Support
- [Ollama Docker GPU](https://docs.ollama.com/docker) - `--gpus=all` flag documentation
- [NVIDIA Container Toolkit](https://itsfoss.com/ollama-docker/) - GPU passthrough setup

### Volume and Persistence
- [Docker Volumes](https://docs.docker.com/engine/storage/volumes/) - Named volumes best practices
- [Ollama Data Persistence](https://hub.docker.com/r/ollama/ollama) - `/root/.ollama` volume mount pattern

---
*Feature research for: CocoSearch v1.6 All-in-One Docker Deployment*
*Researched: 2026-02-01*
