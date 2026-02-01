# Technology Stack: All-in-One Docker with MCP Transports

**Project:** CocoSearch all-in-one Docker deployment
**Researched:** 2026-02-01
**Focus:** Stack additions for multi-service container and MCP SSE/HTTP transport

## Executive Summary

The all-in-one Docker deployment requires three new capabilities:
1. **Process supervision** for running PostgreSQL + Ollama + Python app in one container
2. **Model baking** to include nomic-embed-text (274MB) in the image
3. **HTTP transport** for MCP server (SSE or Streamable HTTP)

The recommended approach uses **s6-overlay** for process management, an **entrypoint script** for Ollama model baking (since `ollama pull --local` is not yet released), and **Streamable HTTP transport** (not SSE) for MCP.

---

## Recommended Stack Additions

### Process Supervisor: s6-overlay

| Component | Version | Purpose | Rationale |
|-----------|---------|---------|-----------|
| s6-overlay | 3.2.2.0 | Multi-process supervision | Container-native, proper PID 1 handling, clean shutdown, health-aware |

**Why s6-overlay over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| s6-overlay | **RECOMMENDED** | Built for containers, accurate health status, fast startup, handles PID 1 properly |
| supervisord | Not recommended | Occupies PID 1 but doesn't reflect child health; container orchestrators get wrong status |
| Custom entrypoint script | Acceptable for simple cases | Works but no automatic restart, no dependency ordering, no graceful shutdown |
| systemd | Not recommended | Overkill, not container-native, heavy |
| tini/dumb-init | Insufficient | Only handles zombie reaping, not process supervision |

**Installation in Dockerfile:**

```dockerfile
ARG S6_OVERLAY_VERSION="3.2.2.0"

# Download and extract s6-overlay (for x86_64)
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz

ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz

# Optional: symlinks for easier service management
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-symlinks-noarch.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-symlinks-noarch.tar.xz

ENTRYPOINT ["/init"]
```

**Source:** [s6-overlay GitHub releases](https://github.com/just-containers/s6-overlay/releases) - HIGH confidence

---

### MCP Transport: Streamable HTTP (not SSE)

| Component | Version | Purpose | Rationale |
|-----------|---------|---------|-----------|
| mcp[cli] | >=1.26.0 (current) | MCP server SDK | Already in pyproject.toml |
| FastMCP transport | `streamable-http` | HTTP-based MCP | SSE is deprecated; Streamable HTTP is recommended for production |

**Why Streamable HTTP over SSE:**

| Transport | Status | Use Case |
|-----------|--------|----------|
| stdio | Supported | Local CLI, Claude Desktop subprocess |
| SSE | **DEPRECATED** | Legacy only, "being superseded by StreamableHTTP" |
| streamable-http | **RECOMMENDED** | Production HTTP deployments, bidirectional streaming |

**Code change required in `src/cocosearch/mcp/server.py`:**

```python
def run_server(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP server with specified transport.

    Args:
        transport: "stdio" for CLI/Claude Desktop, "streamable-http" for Docker
        host: HTTP host (only for HTTP transport)
        port: HTTP port (only for HTTP transport)
    """
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            stateless_http=False,  # Maintain session state
            json_response=False,   # Use SSE for responses (more efficient)
        )
    else:
        raise ValueError(f"Unsupported transport: {transport}")
```

**Claude Desktop configuration for HTTP transport:**

Claude Desktop does not natively support HTTP MCP servers on free plans. Use `mcp-remote` as a bridge:

```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

For Claude Pro/Max/Team/Enterprise (as of mid-2025), native remote server support is available via Settings > Integrations > Add Custom Integration.

**Sources:**
- [FastMCP Running Server docs](https://gofastmcp.com/deployment/running-server) - HIGH confidence
- [MCP Python SDK DeepWiki](https://deepwiki.com/modelcontextprotocol/python-sdk/9.1-running-servers) - HIGH confidence
- [PyPI mcp package](https://pypi.org/project/mcp/) - HIGH confidence

---

### Ollama Model Baking

| Component | Version | Purpose | Rationale |
|-----------|---------|---------|-----------|
| ollama | 0.15.2 (latest) | LLM runtime | Current stable release |
| nomic-embed-text | latest (274MB) | Embedding model | Already used by project |

**Challenge:** Ollama requires `ollama serve` running before `ollama pull` works. The `--local` flag for serverless pull is not yet released.

**Recommended approach: Entrypoint script that pulls on first start**

```dockerfile
FROM ollama/ollama:0.15.2 as ollama-base

# In multi-stage build, copy ollama binary
COPY --from=ollama-base /bin/ollama /usr/local/bin/ollama
```

**Entrypoint script for model pulling:**

```bash
#!/bin/bash
# /etc/s6-overlay/s6-rc.d/ollama/run

# Start ollama serve in background
ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
until ollama list >/dev/null 2>&1; do
    sleep 1
done

# Pull model if not present
if ! ollama list | grep -q "nomic-embed-text"; then
    ollama pull nomic-embed-text
fi

# Keep ollama running
wait $OLLAMA_PID
```

**Alternative: Pre-baked image via multi-stage build**

For truly "baked-in" models (no download on first run), use a dedicated model-loader image:

```dockerfile
FROM ollama/ollama:0.15.2 as model-builder
RUN ollama serve & sleep 5 && ollama pull nomic-embed-text && pkill ollama

FROM ollama/ollama:0.15.2
COPY --from=model-builder /root/.ollama /root/.ollama
```

**Trade-offs:**

| Approach | Image Size | First Start | Complexity |
|----------|-----------|-------------|------------|
| Entrypoint pull | Smaller (~1GB) | Slower (downloads model) | Simple |
| Pre-baked model | Larger (~1.3GB) | Fast (model ready) | More complex build |

**Recommendation:** Start with entrypoint pull for simplicity. Pre-baked can be added later as optimization.

**Sources:**
- [Ollama GitHub Issue #3369](https://github.com/ollama/ollama/issues/3369) - MEDIUM confidence
- [DoltHub blog: Pull-first Ollama](https://www.dolthub.com/blog/2025-03-19-a-pull-first-ollama-docker-image/) - MEDIUM confidence
- [Ollama model page](https://ollama.com/library/nomic-embed-text) - HIGH confidence

---

### PostgreSQL with pgvector

| Component | Version | Purpose | Rationale |
|-----------|---------|---------|-----------|
| pgvector/pgvector | pg17 | Vector database | Already used, current version |

**No changes needed.** The existing `pgvector/pgvector:pg17` image works in a multi-service container.

**s6 service configuration:**

```bash
#!/bin/bash
# /etc/s6-overlay/s6-rc.d/postgres/run
exec postgres -D /var/lib/postgresql/data
```

**Data persistence:** Mount `/var/lib/postgresql/data` as a volume.

---

## Full Stack Summary

### Existing (No Changes)

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | >=3.11 | Runtime |
| cocoindex[embeddings] | >=0.3.28 | Indexing engine |
| mcp[cli] | >=1.26.0 | MCP SDK |
| pgvector | >=0.4.2 | Vector operations |
| psycopg[binary,pool] | >=3.3.2 | PostgreSQL driver |
| pgvector/pgvector:pg17 | pg17 | Database image |
| ollama/ollama | 0.15.2 | LLM server image |

### New Additions

| Component | Version | Purpose |
|-----------|---------|---------|
| s6-overlay | 3.2.2.0 | Process supervision |
| nomic-embed-text | latest (274MB) | Baked embedding model |

### Configuration Changes

| Component | Change |
|-----------|--------|
| FastMCP | Add `streamable-http` transport option |
| CLI | Add `--transport` and `--port` flags to `mcp` command |

---

## What NOT to Add

| Component | Reason |
|-----------|--------|
| supervisord | Not container-native, inaccurate health reporting |
| nginx/caddy | Not needed for single-container; FastMCP handles HTTP |
| SSE transport | Deprecated in favor of Streamable HTTP |
| systemd | Overkill for container |
| Custom init (tini/dumb-init) | s6-overlay provides this plus supervision |
| uvicorn | FastMCP includes Starlette/ASGI server internally |

---

## Installation Commands

No new Python packages required. The existing `mcp[cli]>=1.26.0` already includes all transport support.

```bash
# No pip changes needed - existing dependencies sufficient
```

For Docker build, s6-overlay is installed via tarball extraction (see Dockerfile example above).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| s6-overlay version/install | HIGH | Verified via GitHub releases page |
| MCP transport options | HIGH | Verified via FastMCP docs and Python SDK |
| SSE deprecation | HIGH | Official docs state "being superseded" |
| Ollama model baking | MEDIUM | Workaround approach; `--local` flag not yet released |
| nomic-embed-text size | HIGH | Verified via Ollama model page (274MB) |

---

## Sources

- [s6-overlay GitHub](https://github.com/just-containers/s6-overlay) - Process supervisor
- [FastMCP Running Server](https://gofastmcp.com/deployment/running-server) - Transport options
- [MCP Python SDK](https://pypi.org/project/mcp/) - SDK version 1.26.0
- [Ollama Docker Hub](https://hub.docker.com/r/ollama/ollama) - Container image
- [Ollama nomic-embed-text](https://ollama.com/library/nomic-embed-text) - Model details (274MB)
- [pgvector Docker Hub](https://hub.docker.com/r/pgvector/pgvector) - Database image
- [Claude Desktop MCP Integration](https://gofastmcp.com/integrations/claude-desktop) - Client config
