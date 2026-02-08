# Technology Stack: v1.10 Infrastructure & Protocol Enhancements

**Project:** CocoSearch v1.10
**Researched:** 2026-02-08
**Scope:** Docker simplification, MCP Roots, HTTP query params, parse failure tracking, default DATABASE_URL

## Executive Summary

v1.10 is a refinement milestone. No new major dependencies are required. The enhancements build on existing libraries (MCP SDK v1.26.0 already supports Roots; Starlette already supports query params; Docker simplification removes complexity rather than adding it). The primary work is architectural restructuring and new code patterns within the existing stack.

---

## Recommended Stack

### Existing Dependencies (No Version Changes)

| Technology | Current Version | Purpose | v1.10 Role |
|---|---|---|---|
| `mcp[cli]` | `>=1.26.0` | MCP SDK with FastMCP | Roots support already present in v1.26.0 |
| `starlette` | (transitive via mcp) | HTTP framework | Query parameter access via `Request.query_params` |
| `psycopg[binary,pool]` | `>=3.3.2` | PostgreSQL driver | Parse failure tracking in stats queries |
| `tree-sitter` | `>=0.25.0,<0.26.0` | Code parsing | Parse failure detection source |
| `pyyaml` | `>=6.0.2` | Config parsing | No change |

### Docker Infrastructure (Simplified)

| Technology | Version | Purpose | Change |
|---|---|---|---|
| `pgvector/pgvector` | `pg17` (pgvector 0.8.1) | PostgreSQL + pgvector | Promoted from docker-compose.yml to primary Dockerfile |
| `ollama/ollama` | `latest` | Embedding model server | Remains in image, model pre-baked at build |
| `s6-overlay` | `3.2.2.0` | Process supervision | Retained for PostgreSQL + Ollama management |

### No New Dependencies Required

The following capabilities are already available:

1. **MCP Roots**: `mcp.server.session.ServerSession.list_roots()` -- exists in SDK v1.26.0
2. **HTTP Query Params**: `starlette.requests.Request.query_params` -- built into Starlette
3. **Parse Failure Tracking**: Standard Python exception handling + existing psycopg queries
4. **Default DATABASE_URL**: Standard Python `os.getenv()` with fallback value
5. **Docker Simplification**: Dockerfile restructuring only, no new base images

---

## Detailed Technology Analysis

### 1. MCP Roots Capability

**Confidence: HIGH** (verified against installed SDK source code at `.venv/lib/python3.11/site-packages/mcp/`)

#### What Exists in mcp v1.26.0

The MCP Python SDK v1.26.0 (currently installed) has complete Roots support:

**Types** (from `mcp.types`):
- `Root` -- a root object with `uri` (file:// URI) and optional `name`
- `RootsCapability` -- capability declaration with `listChanged` bool
- `ListRootsRequest` -- JSON-RPC request for `roots/list`
- `ListRootsResult` -- response containing `roots: list[Root]`
- `RootsListChangedNotification` -- notification for `notifications/roots/list_changed`

**Server Session** (from `mcp.server.session.ServerSession`):
```python
async def list_roots(self) -> types.ListRootsResult:
    """Send a roots/list request."""
    return await self.send_request(
        types.ServerRequest(types.ListRootsRequest()),
        types.ListRootsResult,
    )
```

**FastMCP Context** (from `mcp.server.fastmcp.server.Context`):
```python
@property
def session(self):
    """Access to the underlying session for advanced usage."""
    return self.request_context.session
```

**Client capabilities check** (from `mcp.server.session`):
```python
# During initialization, client capabilities are negotiated
# Client declares: {"capabilities": {"roots": {"listChanged": true}}}
# Server can check if roots is supported via the session
```

#### How to Use in CocoSearch Tools

The pattern for accessing roots from within a tool:

```python
from mcp.server.fastmcp import Context

@mcp.tool()
async def search_code(query: str, ctx: Context) -> list[dict]:
    # Request roots from the client
    try:
        roots_result = await ctx.session.list_roots()
        for root in roots_result.roots:
            # root.uri is a file:// URI (e.g., file:///home/user/project)
            # root.name is an optional display name
            pass
    except Exception:
        # Client may not support roots (fallback to existing behavior)
        pass
```

#### Critical Constraint: Stateless HTTP Cannot Use Roots

**Confidence: HIGH** (verified via GitHub issue #1097 and fix PR #1827)

`list_roots()` is a server-to-client request. It requires a bidirectional session. In stateless HTTP mode (`stateless_http=True`), the server cannot send requests to the client because there is no persistent session. Attempting to call `list_roots()` in stateless mode now raises `RuntimeError` (previously it hung indefinitely).

**Implication for CocoSearch:**
- **stdio transport**: Roots fully supported (bidirectional pipe)
- **SSE transport**: Roots fully supported (bidirectional via SSE stream)
- **Streamable HTTP (stateful, default)**: Roots supported (session-based)
- **Streamable HTTP (stateless)**: Roots NOT supported

CocoSearch currently uses `mcp.run(transport="streamable-http")` which defaults to stateful mode. Roots will work out of the box. However, the feature must gracefully degrade when roots are unavailable (client doesn't declare `roots` capability, or transport doesn't support it).

#### MCP Roots Protocol Flow

1. During initialization, the client declares: `{"capabilities": {"roots": {"listChanged": true}}}`
2. Server checks if client supports roots before calling `list_roots()`
3. Server calls `await session.list_roots()` to get `ListRootsResult` with `roots: list[Root]`
4. Each `Root` has `uri` (must be `file://` URI) and optional `name`
5. If roots change, client sends `notifications/roots/list_changed`

#### Integration Plan for CocoSearch

Currently, CocoSearch uses `COCOSEARCH_PROJECT_PATH` env var and `find_project_root()` for project detection. Roots provides a cleaner, protocol-native alternative:

**Priority chain for project detection (proposed):**
1. Explicit `index_name` parameter (user specified)
2. MCP Roots (if client provides roots, use first root as project path)
3. `COCOSEARCH_PROJECT_PATH` env var (existing fallback for `--project-from-cwd`)
4. `find_project_root()` from cwd (existing fallback)

**What NOT to do:**
- Do NOT make Roots required -- many clients don't support it yet
- Do NOT call `list_roots()` on every tool invocation -- cache roots at session level or call once per search
- Do NOT assume roots contain exactly one entry -- handle zero and multiple roots

#### Tool Signature Change Required

Current tools are synchronous (`def search_code`). To use `list_roots()` (which is `async`), tools must become async:

```python
# Current (sync)
@mcp.tool()
def search_code(query: str, ...) -> list[dict]:

# Required for Roots (async with Context)
@mcp.tool()
async def search_code(query: str, ctx: Context, ...) -> list[dict]:
```

FastMCP supports both sync and async tools, so this is a non-breaking change within the framework.

#### Recommendation

Use `mcp[cli]>=1.26.0` (no version change needed). The Roots API is available through `Context.session.list_roots()`. Implement as an optional enhancement to project detection with graceful fallback. Convert relevant tools to async to accept Context.

---

### 2. HTTP Transport Query Parameters for Project Context

**Confidence: HIGH** (verified against installed Starlette source and MCP SDK)

#### The Problem

When CocoSearch runs via HTTP transport (Docker container / remote server), the client may want to specify which project to search without using Roots. Currently, this requires setting `COCOSEARCH_PROJECT_PATH` env var before starting the server, which is static per-server-lifetime.

#### Available Mechanisms

**Option A: ContextVar Middleware (RECOMMENDED)**

The MCP protocol layer abstracts the HTTP transport. Query parameters on the `/mcp` endpoint URL are NOT accessible from within MCP tool functions through the standard Context API. The `RequestContext` in SDK v1.26.0 contains `session`, `lifespan_context`, `request_id`, and `meta` -- but not the Starlette HTTP `Request` object.

To bridge this gap, use a Starlette middleware + `contextvars.ContextVar`:

```python
from contextvars import ContextVar
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Module-level context variable
project_context_var: ContextVar[str | None] = ContextVar("project_context", default=None)

class ProjectContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        project = request.query_params.get("project")
        token = project_context_var.set(project)
        try:
            response = await call_next(request)
            return response
        finally:
            project_context_var.reset(token)

# In tool:
@mcp.tool()
async def search_code(query: str, ...) -> list[dict]:
    project_path = project_context_var.get()  # From URL ?project=<path>
```

**No new dependencies needed.** `ContextVar` is Python stdlib, `BaseHTTPMiddleware` is Starlette built-in.

**Option B: Custom Route (alternative for non-MCP access)**

The existing `@mcp.custom_route()` pattern works well for REST-style endpoints. The `/api/stats` route already uses `request.query_params.get("index")`. But this does NOT help for MCP tool invocations.

**Option C: Stateful session initialization (alternative)**

Store project context during MCP session initialization via a custom lifespan. More complex but eliminates per-request overhead.

#### How Middleware Integrates with FastMCP

FastMCP's ASGI app is a Starlette application. Middleware can be added:

```python
# Method 1: Via FastMCP settings
mcp = FastMCP("cocosearch")
# Starlette middleware list available via mcp._custom_starlette_routes

# Method 2: Wrapping the ASGI app
app = mcp.streamable_http_app()
app.add_middleware(ProjectContextMiddleware)
```

The exact integration point needs validation during implementation, but the pattern is standard Starlette.

#### Recommendation

**Use ContextVar middleware approach:**
1. Accept `?project=<path>` on the MCP endpoint URL
2. Middleware extracts and sets ContextVar before request processing
3. Tools read the ContextVar as another source in the project detection chain
4. This works alongside Roots (Roots for stdio/SSE clients, query params for HTTP clients)

**Priority chain update:**
1. Explicit `index_name` parameter
2. MCP Roots (if available, async)
3. HTTP query param `?project=<path>` (if HTTP transport, via ContextVar)
4. `COCOSEARCH_PROJECT_PATH` env var
5. `find_project_root()` from cwd

---

### 3. Docker Image Simplification

**Confidence: HIGH** (direct analysis of existing Dockerfile and docker-compose.yml)

#### Current State

The all-in-one Dockerfile (170 lines) bundles three services:
1. **PostgreSQL 16** + pgvector extension (installed from apt via pgdg repository)
2. **Ollama** binary + pre-baked nomic-embed-text model (from `ollama/ollama:latest`)
3. **CocoSearch** Python application (built from source via UV)

Managed by s6-overlay with three long-running services (`svc-postgresql`, `svc-ollama`, `svc-mcp`) plus two oneshot services (`init-warmup`, `init-ready`).

#### Target State

Infrastructure-only Docker image:
1. **PostgreSQL** + pgvector extension (KEEP)
2. **Ollama** binary + pre-baked model (KEEP)
3. ~~CocoSearch Python application~~ (REMOVE)

s6-overlay manages two services: `svc-postgresql`, `svc-ollama`.

#### What to Remove from Dockerfile

**Stage 2 (python-builder):** Entire stage removed.
```dockerfile
# REMOVE entire section:
FROM python:3.11-slim AS python-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv venv /app/.venv && uv pip install --python /app/.venv/bin/python .
```

**Stage 3 (runtime):** Remove Python-related lines:
```dockerfile
# REMOVE:
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /build/src /app/src
ENV PATH="/app/.venv/bin:..."
ENV PYTHONPATH="/app/src"
```

#### What to Remove from rootfs

| Path | Action |
|---|---|
| `svc-mcp/run` | DELETE |
| `svc-mcp/type` | DELETE |
| `svc-mcp/dependencies.d/` | DELETE (entire dir) |
| `init-ready/dependencies.d/svc-mcp` | DELETE |
| `user/contents.d/svc-mcp` | DELETE |
| `scripts/health-check` | UPDATE (remove MCP health check, keep PG + Ollama) |

#### What to Update

**Health check:** Remove MCP server check, keep PostgreSQL and Ollama checks only.

**Exposed ports:** Remove 3000 (MCP), keep 5432 (PostgreSQL) and 11434 (Ollama).

**Environment variables:** Remove `COCOSEARCH_MCP_PORT`, `COCOSEARCH_MCP_TRANSPORT`, `COCOSEARCH_LOG_LEVEL`. Keep database and Ollama config.

**Labels:** Change to "CocoSearch Infrastructure" to reflect purpose.

#### Base Image Decision

| Option | Image Size | Pros | Cons |
|---|---|---|---|
| `python:3.11-slim` (current) | ~150MB base | Python available for debugging | Unnecessary 80MB for infra-only |
| `debian:bookworm-slim` | ~70MB base | Smaller, clearer intent | Need to install any debug tools separately |
| `ubuntu:24.04` | ~75MB base | Familiar, well-supported | Slightly larger than Debian slim |

**Recommendation:** Switch to `debian:bookworm-slim`. The infra image has no Python code. Removing Python clearly signals this is infrastructure-only and saves ~80MB.

#### PostgreSQL Version Upgrade

Current Dockerfile installs PostgreSQL 16. The docker-compose.yml uses `pgvector/pgvector:pg17`. Align both to pg17.

**Change in Dockerfile:**
```dockerfile
# FROM:
apt-get install -y postgresql-16 postgresql-16-pgvector
# TO:
apt-get install -y postgresql-17 postgresql-17-pgvector
```

**Also update:** PATH reference from `/usr/lib/postgresql/16/bin` to `/usr/lib/postgresql/17/bin`.

#### Available pgvector Docker Tags (for docker-compose.yml reference)

| Tag | PostgreSQL | pgvector | Status |
|---|---|---|---|
| `pg17` | 17.x | 0.8.1 | Recommended, matches docker-compose.yml |
| `pg18` | 18.x | 0.8.1 | Available but too new for production |
| `pg16` | 16.x | 0.8.1 | Current in Dockerfile, upgrade to pg17 |

#### Recommendation

Remove Python builder stage and svc-mcp from the image. Switch base to `debian:bookworm-slim`. Upgrade PostgreSQL from 16 to 17. Keep s6-overlay for process management of PostgreSQL + Ollama.

---

### 4. Parse Failure Tracking in Stats

**Confidence: HIGH** (analyzed existing code in `indexer/symbols.py` and `management/stats.py`)

#### Current State

Symbol extraction in `indexer/symbols.py` calls `parser.parse()` and `Query()` via tree-sitter. Parse errors are currently silently handled -- tree-sitter returns partial trees on error, and the query simply captures nothing from error nodes. There is no tracking of files/chunks that failed to parse or had parse errors.

#### tree-sitter Parse Error Detection

The `has_error` property is already available in tree-sitter 0.25.x:

```python
# Already available, no new library needed:
tree = parser.parse(bytes(chunk_text, "utf8"))
if tree.root_node.has_error:
    # Parse had errors -- tree-sitter produced partial/error nodes
    # This means the source code had syntax errors
    pass
```

The `has_error` property is recursive: if any descendant node is an ERROR node, the root's `has_error` is True.

#### Storage Options

| Option | Complexity | Persistence | Migration Risk |
|---|---|---|---|
| A. Column in index table | Medium | Permanent | Requires schema migration |
| B. Metadata table aggregates | Low | Permanent | No schema change to index table |
| C. Runtime stats only | Minimal | Lost on restart | No database changes |

**Recommendation:** Option B (metadata table). Store aggregate counts in `cocosearch_index_metadata`:

- `parse_failures_count`: Total chunks with parse errors
- `parse_failures_files`: Number of files with at least one parse error

This keeps the main index table unchanged while providing useful diagnostics. The `cocosearch_index_metadata` table already exists and is used for staleness tracking.

#### Implementation Points

1. **Detection:** In `indexer/symbols.py`, after `parser.parse()`, check `tree.root_node.has_error`
2. **Aggregation:** Count failures during indexing pass
3. **Storage:** Write counts to metadata table after indexing completes
4. **Display:** Add to `stats_command()` output and `index_stats()` MCP tool
5. **API:** Include in `/api/stats` JSON response

**Technology needed:** No new libraries. Uses existing `psycopg`, `tree-sitter`, and stats infrastructure.

---

### 5. Default COCOSEARCH_DATABASE_URL

**Confidence: HIGH** (analyzed `env_validation.py`, `search/db.py`, `indexer/flow.py`)

#### Current State

`COCOSEARCH_DATABASE_URL` is required. If not set:
- `env_validation.py` reports it as an error
- `search/db.py` raises `ValueError("Missing COCOSEARCH_DATABASE_URL")`
- `indexer/flow.py` raises `ValueError("Missing COCOSEARCH_DATABASE_URL")`

#### Proposed Default

```
postgresql://cocosearch:cocosearch@localhost:5432/cocosearch
```

This matches the Docker image's PostgreSQL configuration exactly (user: `cocosearch`, password: `cocosearch`, database: `cocosearch` on localhost:5432).

#### Change Points

| File | Current | Proposed |
|---|---|---|
| `config/env_validation.py` | Error if missing | Warning if using default, not error |
| `search/db.py` | `os.getenv("COCOSEARCH_DATABASE_URL")` | `os.getenv("COCOSEARCH_DATABASE_URL", DEFAULT_DB_URL)` |
| `indexer/flow.py` | `os.getenv("COCOSEARCH_DATABASE_URL")` | `os.getenv("COCOSEARCH_DATABASE_URL", DEFAULT_DB_URL)` |
| CLI `config check` | Shows error when missing | Shows "default" as source |

#### Implementation

Define constant in one place (e.g., `config/__init__.py`):
```python
DEFAULT_DATABASE_URL = "postgresql://cocosearch:cocosearch@localhost:5432/cocosearch"
```

Then reference it everywhere via import. No new libraries needed.

#### Risk Mitigation

Users might accidentally connect to a wrong database if they have PostgreSQL on localhost:5432 with matching credentials. Mitigation:
- Show clear "Using default database URL" message on startup (to stderr)
- `config check` command shows the source as "default" (not "environment")
- Documentation notes this default assumes companion Docker infrastructure

---

## Alternatives Considered

### MCP Roots Alternatives

| Approach | Recommended | Alternative | Why Not |
|---|---|---|---|
| Project detection | MCP Roots via `session.list_roots()` | Separate MCP Resource endpoint | Roots is protocol-native; resources are for data, not config |
| Fallback | Graceful degradation chain | Require Roots support | Most clients don't support Roots yet |

### HTTP Query Param Alternatives

| Approach | Recommended | Alternative | Why Not |
|---|---|---|---|
| Passing context | ContextVar middleware | Custom MCP tool parameter | Middleware preserves clean tool API |
| URL format | `?project=<path>` query param | HTTP headers | Query params are simpler, visible in URL, easier to configure in client configs |

### Docker Simplification Alternatives

| Approach | Recommended | Alternative | Why Not |
|---|---|---|---|
| Base image | `debian:bookworm-slim` | `python:3.11-slim` | No Python needed in infra-only image |
| PostgreSQL | apt from pgdg (pg17) | `pgvector/pgvector:pg17` base | Need unified image with Ollama |
| Process manager | s6-overlay | supervisord | s6-overlay already working, lighter weight |

### Parse Failure Tracking Alternatives

| Approach | Recommended | Alternative | Why Not |
|---|---|---|---|
| Storage | Metadata table aggregate counts | Per-chunk column | Metadata table is simpler, less migration risk |
| Detection | `tree.root_node.has_error` | Custom error counting | Built-in tree-sitter property is sufficient |

---

## What NOT to Use

| Technology | Why NOT |
|---|---|
| FastMCP 2.x / 3.x (standalone `fastmcp` package) | CocoSearch uses `mcp[cli]` which bundles its own FastMCP. The standalone `fastmcp` PyPI package (now at 3.0.0b2) is a DIFFERENT project with a different API. Do NOT install both -- they conflict. |
| `mcp` v2.x (pre-alpha) | v2 SDK is not production-ready (pre-alpha, targeting Q1 2026). Stay on v1.26.x. |
| `stateless_http=True` | Breaks Roots support entirely. CocoSearch needs stateful HTTP for server-to-client requests. |
| Docker multi-container for all-in-one | The point of the infra image is single-container simplicity with s6-overlay. |
| `supervisord` | Heavier than s6-overlay, would be a regression from current working setup. |
| pgvector alternatives (pgvecto.rs, VectorChord) | pgvector is the standard, well-supported, already working. No reason to switch. |
| `python:3.11-slim` as infra base | Adds ~80MB for unused Python runtime in an infra-only image. |

---

## Version Pinning Summary

### pyproject.toml -- No Changes Needed

```toml
dependencies = [
    "cocoindex[embeddings]>=0.3.28",
    "mcp[cli]>=1.26.0",           # Already has Roots, Context, session API
    "pathspec>=1.0.3",
    "pgvector>=0.4.2",
    "psycopg[binary,pool]>=3.3.2",
    "pyyaml>=6.0.2",
    "rich>=13.0.0",
    "tree-sitter>=0.25.0,<0.26.0", # has_error property available
    "tree-sitter-language-pack>=0.13.0",
]
```

No dependency additions or version changes required for v1.10.

### Docker Image Versions

| Component | Current | Recommended | Rationale |
|---|---|---|---|
| Base image | `python:3.11-slim` | `debian:bookworm-slim` | No Python needed in infra-only |
| PostgreSQL | 16 (from apt) | 17 (from apt) | Align with docker-compose.yml |
| pgvector extension | `postgresql-16-pgvector` | `postgresql-17-pgvector` | Follows PG version |
| Ollama | `ollama/ollama:latest` | `ollama/ollama:latest` | No change |
| s6-overlay | `3.2.2.0` | `3.2.2.0` | No change needed |
| Embedded model | `nomic-embed-text` | `nomic-embed-text` | No change |

---

## Confidence Assessment

| Area | Confidence | Reason |
|---|---|---|
| MCP Roots API | HIGH | Verified against installed SDK v1.26.0 source code -- types, session method, and context access all confirmed |
| Stateless HTTP limitation | HIGH | Verified via GitHub issue #1097, fix in PR #1827 -- stateless mode raises RuntimeError on list_roots() |
| HTTP query param middleware | MEDIUM | ContextVar + Starlette middleware is standard pattern, but exact FastMCP middleware integration needs validation during implementation |
| Docker simplification | HIGH | Direct analysis of current Dockerfile -- removal scope is clear and well-defined |
| Parse failure detection | HIGH | `tree.root_node.has_error` is documented tree-sitter API, available in 0.25.x |
| Default DATABASE_URL | HIGH | Straightforward `os.getenv()` with default -- all change points identified |

**Overall confidence: HIGH**

---

## Sources

### HIGH Confidence (verified against installed code / official spec)

- MCP SDK v1.26.0 installed source: `.venv/lib/python3.11/site-packages/mcp/`
  - `types.py` lines 1676-1736: Root, RootsCapability, ListRootsRequest, ListRootsResult, RootsListChangedNotification
  - `server/session.py` lines 350-355: `list_roots()` async method
  - `server/fastmcp/server.py` lines 1098-1300: Context class with `session` property
  - `shared/context.py`: RequestContext dataclass (session, lifespan_context, request_id, meta -- no HTTP request)
  - `server/streamable_http.py`: Transport implementation (no query_params access)
- MCP Specification 2025-11-25 Roots: https://modelcontextprotocol.io/specification/2025-11-25/client/roots
- MCP PyPI page (v1.26.0, Jan 24 2026): https://pypi.org/project/mcp/
- pgvector/pgvector Docker tags (0.8.1, pg13-pg18): https://hub.docker.com/r/pgvector/pgvector/tags
- CocoSearch source code: `src/cocosearch/mcp/server.py`, `src/cocosearch/config/env_validation.py`, `src/cocosearch/indexer/symbols.py`, `docker/Dockerfile`

### MEDIUM Confidence (official docs + community verification)

- FastMCP Context API docs: https://gofastmcp.com/python-sdk/fastmcp-server-context
- MCP Python SDK repository: https://github.com/modelcontextprotocol/python-sdk
- Stateless HTTP roots hang fix (issue #1097): https://github.com/modelcontextprotocol/python-sdk/issues/1097
- HTTP headers in tools (issue #750): https://github.com/modelcontextprotocol/python-sdk/issues/750
- Starlette Request API: https://www.starlette.io/requests/

### LOW Confidence (single source / blog posts)

- FastMCP 3.0.0b2 pre-release (Feb 2026): https://pypi.org/project/fastmcp/ -- NOT relevant to `mcp[cli]` bundled FastMCP
- MCP Roots overview blog: https://www.mcpevals.io/blog/roots-mcp
