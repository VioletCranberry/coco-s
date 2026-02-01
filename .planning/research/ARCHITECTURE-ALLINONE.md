# Architecture Patterns: All-in-One Docker Integration

**Domain:** MCP Server with embedded infrastructure
**Researched:** 2026-02-01
**Confidence:** HIGH (verified with official docs and existing codebase)

## Executive Summary

This document details how an all-in-one Docker image integrates with CocoSearch's existing MCP server and multi-service architecture. The key insight: the existing architecture already supports this pattern - we need to add transport flexibility and process supervision, not fundamental restructuring.

## Current Architecture Analysis

### Existing Components

```
docker-compose.yml (separate containers)
├── db (pgvector/pgvector:pg17)
│   └── Port 5432, volume: postgres_data
└── ollama (ollama/ollama:latest)
    └── Port 11434, volume: ollama_data

src/cocosearch/
├── mcp/server.py         # FastMCP server, stdio transport
├── search/db.py          # Connection pool, reads COCOSEARCH_DATABASE_URL
├── config/loader.py      # Finds cocosearch.yaml in cwd or git root
└── cli.py                # Entry points: cocosearch mcp, index, search
```

### Current Data Flow

```
Claude Desktop (stdio) --> cocosearch mcp --> COCOSEARCH_DATABASE_URL --> PostgreSQL
                                          \-> cocoindex.init() --> OLLAMA_URL --> Ollama
```

### Integration Points

| Component | Current State | All-in-One Impact |
|-----------|--------------|-------------------|
| `server.py` | `mcp.run(transport="stdio")` | Add SSE/HTTP transport option |
| `db.py` | Reads `COCOSEARCH_DATABASE_URL` env | Set to `localhost:5432` internally |
| `config/loader.py` | Finds `cocosearch.yaml` in cwd | Mount point for user's project |
| `docker-compose.yml` | Separate containers | Keep for dev, all-in-one for deploy |
| `dev-setup.sh` | Bootstraps compose env | Unchanged, dev workflow |

## Recommended Architecture

### All-in-One Container Structure

```
cocosearch-aio (single container)
├── /init (s6-overlay entrypoint)
│
├── /etc/s6-overlay/s6-rc.d/
│   ├── postgres/           # PostgreSQL service
│   │   ├── type            # "longrun"
│   │   ├── run             # Start postgres
│   │   └── dependencies.d/
│   │       └── base        # Starts after base initialization
│   │
│   ├── ollama/             # Ollama service
│   │   ├── type            # "longrun"
│   │   ├── run             # Start ollama serve
│   │   └── dependencies.d/
│   │       └── base
│   │
│   ├── model-pull/         # One-shot: pull embedding model
│   │   ├── type            # "oneshot"
│   │   ├── up              # ollama pull nomic-embed-text
│   │   └── dependencies.d/
│   │       └── ollama      # After ollama is running
│   │
│   └── cocosearch/         # MCP server
│       ├── type            # "longrun"
│       ├── run             # Start cocosearch with SSE transport
│       └── dependencies.d/
│           ├── postgres
│           └── model-pull  # After model is available
│
├── /var/lib/postgresql/    # PostgreSQL data
├── /root/.ollama/          # Ollama models
└── /project/               # Mount point for user's codebase
```

### Transport Modes

**Current:** Only stdio (line 201 of server.py)
```python
def run_server():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")
```

**Proposed:** Transport selection via environment variable
```python
def run_server():
    """Run the MCP server."""
    transport = os.getenv("COCOSEARCH_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=8080)
    elif transport == "http":
        mcp.run(transport="http", host="0.0.0.0", port=8080)
    else:
        mcp.run(transport="stdio")
```

### Claude Desktop Configuration Options

**Option A: Direct Docker (SSE/HTTP) - Requires Claude Pro/Max/Team/Enterprise**
```json
{
  "mcpServers": {
    "cocosearch": {
      "url": "http://localhost:8080/mcp/"
    }
  }
}
```

**Option B: Docker with mcp-remote proxy (All tiers)**
```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "npx",
      "args": [
        "mcp-remote@latest",
        "http://localhost:8080/mcp/"
      ]
    }
  }
}
```

**Option C: stdio via docker exec (All tiers)**
```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "docker",
      "args": [
        "exec", "-i", "cocosearch-aio",
        "cocosearch", "mcp"
      ]
    }
  }
}
```

## New Components Needed

| Component | Purpose | Location |
|-----------|---------|----------|
| `Dockerfile.aio` | All-in-one image build | `/Dockerfile.aio` |
| s6-overlay services | Process supervision | `/etc/s6-overlay/s6-rc.d/` |
| Transport selection | SSE/HTTP support | Modify `server.py` |
| Health check endpoint | Container readiness | New or via FastMCP |
| Entrypoint script | Environment setup | `/docker-entrypoint.sh` |

### Modified Components

| Component | Change Required |
|-----------|-----------------|
| `src/cocosearch/mcp/server.py` | Add transport parameter, default stdio |
| `pyproject.toml` | Add `cocosearch-aio` entry point if needed |
| `docker-compose.yml` | Add `aio` service profile (optional) |

## Data Flow: All-in-One Mode

```
Claude Desktop
     │
     ├── (Option A/B: HTTP/SSE on port 8080)
     │   └── cocosearch MCP server
     │
     └── (Option C: docker exec stdio)
         └── cocosearch MCP server
                   │
                   ├── localhost:5432 (PostgreSQL in same container)
                   │   └── pgvector for embeddings
                   │
                   └── localhost:11434 (Ollama in same container)
                       └── nomic-embed-text model

User's codebase mounted at /project
└── cocosearch.yaml auto-discovered
```

## Process Supervision: s6-overlay vs supervisord

**Recommendation: s6-overlay**

| Criterion | s6-overlay | supervisord |
|-----------|------------|-------------|
| Container exit handling | Designed for containers | Runs forever by default |
| Health status accuracy | PID 1 aware | Can mask failures |
| Dependency ordering | Native support | Manual scripting |
| Graceful shutdown | Built-in | Requires configuration |
| Installation | Extract tarball | pip install |
| Container focused | Yes (from ground up) | No (general purpose) |

Source: [s6-overlay GitHub](https://github.com/just-containers/s6-overlay), [Platform Engineers guide](https://platformengineers.io/blog/s6-overlay-quickstart/)

### s6-overlay Service Dependencies

```
base (system init)
  │
  ├── postgres (longrun)
  │     └── Ready when pg_isready succeeds
  │
  └── ollama (longrun)
        │ Ready when ollama list succeeds
        │
        └── model-pull (oneshot)
              │ Completes when nomic-embed-text pulled
              │
              └── cocosearch (longrun)
                    Ready when HTTP health check passes
```

## Build Order Recommendation

Based on dependencies and integration points:

### Phase 1: Transport Flexibility
1. Modify `server.py` to accept transport parameter
2. Add `COCOSEARCH_TRANSPORT` env var handling
3. Test SSE/HTTP transport with existing docker-compose setup

### Phase 2: Dockerfile Creation
1. Create `Dockerfile.aio` with:
   - Base image: `python:3.11-slim`
   - Install PostgreSQL, s6-overlay
   - Copy application
2. Add s6-overlay service definitions
3. Create health check script

### Phase 3: Ollama Integration
1. Add Ollama installation to Dockerfile
2. Create model-pull oneshot service
3. Configure health check dependencies

### Phase 4: User Experience
1. Volume mount for `/project`
2. Documentation for Claude Desktop config
3. Build and publish image

## Entrypoint Strategy

```bash
#!/command/execlineb -S0
# /etc/s6-overlay/s6-rc.d/cocosearch/run

# Set internal URLs (services in same container)
export COCOSEARCH_DATABASE_URL=postgresql://cocoindex:cocoindex@localhost:5432/cocoindex
export COCOSEARCH_TRANSPORT=sse

# Start with SSE transport
exec cocosearch mcp
```

### Environment Variable Defaults (All-in-One Mode)

| Variable | All-in-One Default | User Can Override |
|----------|-------------------|-------------------|
| `COCOSEARCH_DATABASE_URL` | `localhost:5432` | No (internal) |
| `COCOSEARCH_TRANSPORT` | `sse` | Yes (`stdio`, `http`) |
| `COCOSEARCH_PORT` | `8080` | Yes |
| `OLLAMA_URL` | `localhost:11434` | No (internal) |

## Volume Mounts

| Mount | Purpose | Required |
|-------|---------|----------|
| `/project` | User's codebase with `cocosearch.yaml` | Yes |
| `/var/lib/postgresql/data` | Persistent indexes | Recommended |
| `/root/.ollama` | Cached Ollama models | Recommended |

## Health Check Design

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

Note: FastMCP may provide health endpoint automatically. Verify during implementation.

## Anti-Patterns to Avoid

### 1. Foreground Process Confusion
**Wrong:** Running all services in foreground with `&`
**Right:** Use s6-overlay to manage all processes properly

### 2. Hardcoded Paths
**Wrong:** Assuming codebase at fixed path
**Right:** Use `/project` mount point, let config discovery work

### 3. Missing Model on Startup
**Wrong:** Assume model exists
**Right:** Use oneshot service to pull model before cocosearch starts

### 4. Ignoring Transport Mismatch
**Wrong:** Only support SSE (excludes free tier users)
**Right:** Support stdio via `docker exec` for universal compatibility

## Compatibility Matrix

| Claude Tier | Connection Method | Configuration Complexity |
|-------------|------------------|-------------------------|
| Free | `docker exec` (stdio) | Low |
| Pro/Max/Team/Enterprise | HTTP direct or mcp-remote | Low |
| All | `docker exec` (stdio) | Low |

## Sources

- [FastMCP Running Server](https://gofastmcp.com/deployment/running-server) - Transport options documentation
- [FastMCP Claude Desktop](https://gofastmcp.com/integrations/claude-desktop) - Integration patterns
- [Docker Multi-Process Containers](https://docs.docker.com/engine/containers/multi-service_container/) - Official Docker docs
- [s6-overlay GitHub](https://github.com/just-containers/s6-overlay) - Process supervisor
- [Ollama Docker](https://docs.ollama.com/docker) - Container deployment
- [MCP Transport Discussion](https://github.com/orgs/modelcontextprotocol/discussions/16) - SSE vs stdio
- Existing codebase: `server.py`, `db.py`, `config/loader.py`, `docker-compose.yml`
