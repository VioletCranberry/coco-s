# Architecture Patterns: v1.10 Integration

**Domain:** MCP Server, Docker simplification, protocol enhancements, pipeline observability
**Researched:** 2026-02-08
**Confidence:** HIGH (verified against codebase, MCP specification, existing architecture research)

## Executive Summary

The v1.10 changes span four architectural layers: Docker packaging, MCP protocol, HTTP transport, indexing pipeline, and configuration defaults. The critical insight is that these changes are **structurally independent** -- they touch different parts of the codebase with minimal overlap. This means they can be phased by complexity and risk rather than dependency ordering.

The highest-risk change is Docker simplification (removing CocoSearch from the image) because it changes the deployment model. The MCP Roots capability is protocol-level and integrates cleanly with the existing `find_project_root()` detection. HTTP query params require understanding the Starlette/FastMCP middleware stack. Parse failure tracking requires changes to CocoIndex transform functions that run in a Rust-backed pipeline. Default DATABASE_URL is a straightforward config change with one subtle interaction point.

## Current Architecture (As-Is)

### Component Map

```
src/cocosearch/
|-- mcp/server.py              # FastMCP server, 5 tools, custom routes
|-- cli.py                     # CLI entry point, mcp_command() starts server
|-- config/
|   |-- schema.py              # Pydantic models (CocoSearchConfig)
|   |-- loader.py              # YAML file loading
|   |-- resolver.py            # 4-level precedence: CLI > env > config > default
|   |-- env_validation.py      # validate_required_env_vars()
|   `-- env_substitution.py    # ${VAR:-default} syntax in YAML
|-- management/
|   |-- context.py             # find_project_root(), resolve_index_name()
|   |-- stats.py               # IndexStats, get_comprehensive_stats()
|   `-- metadata.py            # cocosearch_index_metadata table
|-- indexer/
|   |-- flow.py                # CocoIndex flow: files -> chunks -> embeddings -> PG
|   |-- symbols.py             # tree-sitter symbol extraction
|   |-- embedder.py            # Ollama embedding via CocoIndex
|   `-- progress.py            # Rich progress display
|-- search/
|   |-- db.py                  # Connection pool, COCOSEARCH_DATABASE_URL
|   |-- hybrid.py              # Vector + keyword RRF fusion
|   `-- cache.py               # LRU query cache
`-- handlers/                  # Language-specific chunking (HCL, Dockerfile, Bash)

docker/
|-- Dockerfile                 # All-in-one: PostgreSQL + Ollama + CocoSearch
`-- rootfs/etc/s6-overlay/
    `-- s6-rc.d/
        |-- svc-postgresql/    # PostgreSQL 16 longrun service
        |-- svc-ollama/        # Ollama longrun service
        |-- svc-mcp/           # CocoSearch MCP longrun service
        |-- init-warmup/       # Ollama model warmup oneshot
        `-- init-ready/        # Ready signal oneshot
```

### Current Data Flow

```
Claude Code (stdio) --> cocosearch mcp --project-from-cwd
    |
    v
find_project_root(os.getcwd())    [management/context.py]
    |
    v
resolve_index_name(root, method)  [management/context.py]
    |
    v
search(query, index_name)         [search/hybrid.py]
    |
    v
COCOSEARCH_DATABASE_URL           [search/db.py -> connection pool]
    |
    v
PostgreSQL (pgvector)             [external service]
```

### Current Docker Service Dependency Chain

```
s6-overlay /init
    |
    +--> svc-postgresql (longrun, notification-fd readiness)
    |        |
    +--> svc-ollama (longrun, notification-fd readiness)
    |        |
    |        +--> init-warmup (oneshot, depends: svc-ollama)
    |                 |
    +--> svc-mcp (longrun, depends: svc-postgresql, svc-ollama, init-warmup)
             |
             +--> init-ready (oneshot, depends: svc-mcp)
```

---

## Change 1: Strip CocoSearch from Docker Image

### What Changes

The Docker image currently bundles three services: PostgreSQL+pgvector, Ollama+model, and CocoSearch MCP server. The change strips CocoSearch from the image, making it **infra-only**: PostgreSQL+pgvector and Ollama+model.

### Architecture Impact

**Components removed:**
- `svc-mcp/` service definition (entire directory)
- `init-ready/` dependency on svc-mcp
- Python build stage in Dockerfile (Stage 2: python-builder)
- Python venv COPY in final stage
- `PYTHONPATH`, `PATH` for `.venv/bin`
- Port 3000 EXPOSE

**Components modified:**
- `init-ready/dependencies.d/` -- replace `svc-mcp` with `svc-ollama` (or `init-warmup`)
- `health-check` script -- remove MCP server check (only PG + Ollama)
- `Dockerfile` -- remove Stage 2 (python-builder), remove Python COPY/ENV lines
- `ready-signal` script -- remove MCP Server line from status output

**Components unchanged:**
- `svc-postgresql/` -- stays identical
- `svc-ollama/` -- stays identical
- `init-warmup/` -- stays identical (warms Ollama model)

### New Dependency Chain

```
s6-overlay /init
    |
    +--> svc-postgresql (longrun)
    |
    +--> svc-ollama (longrun)
    |        |
    |        +--> init-warmup (oneshot, depends: svc-ollama)
    |
    +--> init-ready (oneshot, depends: svc-postgresql, init-warmup)
```

### Dockerfile Changes (Structural)

```
REMOVE: Stage 2 (python-builder) entirely
REMOVE: COPY --from=python-builder lines
REMOVE: ENV PATH="/app/.venv/bin:..." PYTHONPATH="/app/src"
REMOVE: EXPOSE 3000
REMOVE: docker/rootfs/etc/s6-overlay/s6-rc.d/svc-mcp/ (entire directory)
REMOVE: docker/rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/svc-mcp
MODIFY: docker/rootfs/etc/s6-overlay/s6-rc.d/init-ready/dependencies.d/
         - Remove svc-mcp file
         - Add svc-postgresql and init-warmup files
MODIFY: docker/rootfs/etc/s6-overlay/scripts/health-check
         - Remove MCP server curl check
MODIFY: docker/rootfs/etc/s6-overlay/scripts/ready-signal
         - Remove MCP Server line from status output
MODIFY: ENV block
         - Remove COCOSEARCH_MCP_PORT, COCOSEARCH_MCP_TRANSPORT
         - Keep COCOSEARCH_DATABASE_URL (infra uses these creds internally)
```

### Environment Variables After Stripping

| Variable | Keep | Reason |
|----------|------|--------|
| `COCOSEARCH_PG_PORT` | YES | PostgreSQL port configuration |
| `COCOSEARCH_OLLAMA_PORT` | YES | Ollama port configuration |
| `COCOSEARCH_EMBED_MODEL` | YES | Which model to prebake/warmup |
| `COCOSEARCH_DATABASE_URL` | YES | Used by PG init scripts for cred setup |
| `COCOSEARCH_MCP_PORT` | NO | No MCP server in container |
| `COCOSEARCH_MCP_TRANSPORT` | NO | No MCP server in container |
| `COCOSEARCH_LOG_LEVEL` | NO | CocoSearch-specific |
| `OLLAMA_HOST` | YES | Ollama binding config |
| `OLLAMA_MODELS` | YES | Model storage path |
| `PGDATA` | YES | PostgreSQL data directory |
| `S6_KILL_GRACETIME` | YES | s6-overlay shutdown |
| `S6_SERVICES_GRACETIME` | YES | s6-overlay shutdown |

### Risk Assessment

**Low risk.** This is a deletion operation -- removing code is safer than adding. The remaining services (PostgreSQL, Ollama) are unchanged. The key risk is breaking the s6-overlay dependency chain by leaving dangling references to `svc-mcp`.

### Integration Point: docker-compose.yml

The existing `docker-compose.yml` already runs PostgreSQL and Ollama as separate containers (not using the all-in-one image). Two options:

1. **Keep as-is**: `docker-compose.yml` stays separate containers, all-in-one image is alternative
2. **Align credentials**: Change `docker-compose.yml` from `cocoindex:cocoindex` to `cocosearch:cocosearch` to match the all-in-one image and the new default DATABASE_URL

Recommendation: Option 2 (align credentials) because it eliminates the confusing mismatch between dev and Docker deployment.

---

## Change 2: MCP Roots Capability

### Protocol Overview

MCP Roots is a client-to-server capability where clients expose filesystem boundaries. Per the [MCP specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/client/roots):

1. **Client declares** `roots` capability during initialization
2. **Server requests** roots via `roots/list` JSON-RPC method
3. **Client responds** with list of `{uri: "file:///path", name: "..."}`
4. **Client notifies** root changes via `notifications/roots/list_changed`

Key: Roots flow is **server-initiated** -- the server asks the client for roots, not the other way around.

### Integration with Existing Architecture

The existing project detection in `server.py` (lines 214-237) uses `find_project_root(os.getcwd())` or `COCOSEARCH_PROJECT_PATH` env var. Roots would provide a third, protocol-correct source.

**Detection priority chain (proposed):**

```
1. Explicit index_name parameter (highest priority)
2. MCP Roots URI (protocol-correct, client-provided)
3. COCOSEARCH_PROJECT_PATH env var (--project-from-cwd)
4. os.getcwd() via find_project_root() (fallback)
```

### Where to Add Roots Handling

**In `server.py`, inside `search_code()` tool:**

The FastMCP `Context` object provides access to `ctx.session.list_roots()` (verified via [FastMCP context docs](https://gofastmcp.com/python-sdk/fastmcp-server-context)). The server calls this during tool invocation to get the client's active project root.

```
search_code(query, index_name=None, ctx: Context)
    |
    if index_name is None:
    |   |
    |   +--> Try: roots = await ctx.session.list_roots()
    |   |    if roots and roots[0].uri starts with "file://":
    |   |        root_path = Path(uri_to_path(roots[0].uri))
    |   |
    |   +--> Fallback: COCOSEARCH_PROJECT_PATH env var
    |   |
    |   +--> Fallback: find_project_root(os.getcwd())
    |
    resolve_index_name(root_path, detection_method)
```

### Architectural Considerations

**1. Synchronous vs Asynchronous Tool:**
Current `search_code()` is a synchronous function (`def search_code`). Calling `ctx.session.list_roots()` requires `await`. This means `search_code` must become `async def search_code`. FastMCP supports both sync and async tools, so this is a safe change.

**2. Transport Compatibility:**
- **stdio**: Claude Code provides roots (it knows the workspace). Works.
- **SSE/HTTP**: Roots depend on the connecting client. Claude Desktop provides roots. Works.
- **Docker infra-only**: No MCP server in container, so N/A.

**3. Graceful Degradation:**
Not all clients support roots. The server must handle:
- Client without roots capability (method returns error -32601)
- Client with roots but empty list
- Client with multiple roots (use first one)

The `try/except` pattern around `list_roots()` handles this naturally.

**4. File URI Parsing:**
Root URIs are `file:///path/to/dir`. Need a utility to convert:
- `file:///home/user/project` -> `Path("/home/user/project")`
- Handle URL encoding in paths
- Python's `urllib.parse.urlparse` + `unquote` handles this

### Impact on Other Tools

The same roots-based detection should apply to `index_codebase()` (for default path) and `index_stats()` (for default index). Extract the detection logic into a shared helper:

```python
async def _detect_project(ctx: Context) -> tuple[Path | None, str | None]:
    """Detect project root from roots > env > cwd."""
    # 1. Try MCP Roots
    try:
        roots_result = await ctx.session.list_roots()
        if roots_result and roots_result.roots:
            uri = roots_result.roots[0].uri
            if uri.startswith("file://"):
                path = Path(urlparse(uri).path)
                return path, "roots"
    except Exception:
        pass  # Client doesn't support roots

    # 2. Try env var
    project_path_env = os.environ.get("COCOSEARCH_PROJECT_PATH")
    if project_path_env:
        return find_project_root(Path(project_path_env))

    # 3. Fallback to cwd
    return find_project_root()
```

### Where to Place the Helper

**Recommended: `src/cocosearch/mcp/server.py`** (private helper in the server module).

Not in `management/context.py` because roots detection requires MCP session context (`ctx`), which is server-specific. Keep `find_project_root()` transport-agnostic in management.

---

## Change 3: HTTP Transport Query Parameters

### Problem Statement

When clients connect via HTTP/SSE transport (not stdio), there is no inherent working directory. The `--project-from-cwd` pattern works for stdio because the subprocess inherits the parent's cwd. For HTTP, the client needs a way to pass project context at connection time.

### Current HTTP Transport Architecture

```
Client POST /mcp
    |
    FastMCP (Starlette-based)
    |
    +--> mcp.run(transport="streamable-http")
    |
    +--> Starlette ASGI app
         |
         +--> /mcp endpoint (JSON-RPC)
         +--> /health (custom_route)
         +--> /dashboard (custom_route)
         +--> /api/stats (custom_route)
```

### Approach: Query Parameters on MCP Endpoint

The MCP specification does not define how to pass custom data during HTTP connection. The standard approach is to use query parameters on the endpoint URL:

```
http://localhost:3000/mcp?project=/path/to/repo
```

### Integration Architecture

**Option A: Starlette Middleware (Recommended)**

Add a middleware or lifespan handler that extracts `project` from query params and stores it in a way that tools can access.

The challenge: FastMCP's HTTP transport creates a session per connection. Query params from the initial POST need to persist into tool invocations within that session.

**Where query params are available:**
- The Starlette `Request` object in custom routes (already used in `/api/stats`)
- NOT directly available in MCP tool functions (tools get `Context`, not `Request`)

**Proposed architecture:**

1. Add middleware that reads `?project=` from incoming requests
2. Store project path in a `contextvars.ContextVar` (async-safe, per-request)
3. `_detect_project()` helper reads from the context var before falling back to env/cwd

**Option B: Custom Header (Alternative)**

Clients send `X-CocoSearch-Project: /path/to/repo` header. Same architectural constraints as query params.

**Option C: MCP Initialize Request Metadata**

The MCP `initialize` request from the client can include `clientInfo`. Some implementations pass custom data here. However, this is not standardized.

### Recommended Approach

For v1.10, use **query parameters with contextvars-based storage**:

```
POST http://localhost:3000/mcp?project=/path/to/repo
```

Implementation path:
1. In `run_server()`, when transport is HTTP, configure FastMCP with a custom ASGI middleware
2. Middleware extracts `project` query param from the request URL
3. Stores it in a `contextvars.ContextVar` (async-safe per-request state)
4. `_detect_project()` helper reads from context var before falling back to env var

**Key architectural detail:** The FastMCP `streamable-http` transport uses Starlette internally. Starlette supports middleware. The middleware intercepts POST requests to `/mcp`, extracts query params, and stores them using Python `contextvars`.

```python
from contextvars import ContextVar
from urllib.parse import parse_qs

_http_project_path: ContextVar[str | None] = ContextVar('http_project_path', default=None)

class ProjectContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            project = params.get("project", [None])[0]
            if project:
                _http_project_path.set(project)
        await self.app(scope, receive, send)
```

### Detection Chain Integration

The `_detect_project()` helper becomes:
```
1. MCP Roots (protocol-correct)
2. HTTP query param via ContextVar (transport-level)
3. COCOSEARCH_PROJECT_PATH env var (--project-from-cwd)
4. os.getcwd() via find_project_root() (fallback)
```

### Risk Assessment

**Medium risk.** This requires understanding the FastMCP/Starlette middleware stack. The `contextvars` approach is the standard Python pattern for per-request state in async frameworks, but its interaction with FastMCP's session model needs verification during implementation.

**Fallback:** If middleware integration proves difficult, a simpler approach is to only support `?project=` for the first request and store it process-globally (suitable for single-user deployments, which is CocoSearch's target).

---

## Change 4: Parse Failure Tracking

### Problem Statement

The indexing pipeline silently swallows parse errors in symbol extraction (`symbols.py` line 446: catches all exceptions, returns NULLs). Users have no visibility into which files/languages fail to parse.

### Current Pipeline Architecture

```
flow.py: create_code_index_flow()
    |
    for each file:
    |   |
    |   +--> extract_language(filename)        [embedder.py] -- never fails
    |   |
    |   +--> SplitRecursively(text, language)   [CocoIndex Rust] -- may fail silently
    |   |
    |   for each chunk:
    |       |
    |       +--> code_to_embedding(text)        [embedder.py via Ollama] -- may fail
    |       |
    |       +--> extract_devops_metadata(text)   [handlers/__init__.py] -- never fails
    |       |
    |       +--> extract_symbol_metadata(text)   [symbols.py] -- catches errors, returns NULLs
    |       |
    |       +--> text_to_tsvector_sql(text)      [tsvector.py] -- string transform, never fails
    |       |
    |       +--> collect(...)                    [CocoIndex] -- stores in PG
```

### Where Failures Can Occur

| Stage | Component | Failure Mode | Current Handling |
|-------|-----------|--------------|------------------|
| Chunking | `SplitRecursively` | Unknown language, malformed file | CocoIndex internal (opaque) |
| Embedding | `code_to_embedding` | Ollama timeout, model error | CocoIndex error (aborts flow) |
| Metadata | `extract_devops_metadata` | Regex failure | Returns empty strings (safe) |
| Symbols | `extract_symbol_metadata` | tree-sitter parse error | Catches exception, returns NULLs |

The primary tracking target is **symbol extraction failures** because:
1. They are the most visible (users see missing symbols in stats)
2. They are language-specific (C/C++ macros, JS metaprogramming)
3. The code already catches and logs them (`logger.error` on line 448)

### Architecture for Tracking

**Problem:** CocoIndex transform functions (`@cocoindex.op.function()`) run inside CocoIndex's Rust pipeline. They cannot write to external state (no database access, no global counters that survive across pipeline stages).

**Solution: Track in the output schema, aggregate in stats.**

Instead of tracking failures in a separate system, add a `parse_status` field to the symbol extraction return value, which becomes a column in the indexed data:

```
Chunk row in PostgreSQL:
  filename, location, embedding, content_text, ...
  symbol_type, symbol_name, symbol_signature,
  parse_status  <-- NEW: "ok" | "error" | "unsupported" | NULL (pre-v1.10)
```

### Modified Pipeline

```python
@cocoindex.op.function()
def extract_symbol_metadata(text: str, language: str) -> dict:
    ts_language = LANGUAGE_MAP.get(language)

    if ts_language is None:
        return {
            "symbol_type": None,
            "symbol_name": None,
            "symbol_signature": None,
            "parse_status": "unsupported",  # Language has no symbol support
        }

    try:
        query_text = resolve_query_file(ts_language)
        if query_text is None:
            return {... "parse_status": "unsupported"}

        symbols = _extract_symbols_with_query(text, ts_language, query_text)
        if symbols:
            return {**symbols[0], "parse_status": "ok"}
        return {... "parse_status": "ok"}  # Parsed fine, just no symbols found

    except Exception as e:
        logger.error(f"Symbol extraction failed: {e}", exc_info=True)
        return {
            "symbol_type": None,
            "symbol_name": None,
            "symbol_signature": None,
            "parse_status": "error",  # Actual parse failure
        }
```

### Flow Integration

In `flow.py`, add `parse_status` to the collect call:

```python
code_embeddings.collect(
    filename=file["filename"],
    location=chunk["location"],
    embedding=chunk["embedding"],
    content_text=chunk["text"],
    content_tsv_input=chunk["content_tsv_input"],
    block_type=chunk["metadata"]["block_type"],
    hierarchy=chunk["metadata"]["hierarchy"],
    language_id=chunk["metadata"]["language_id"],
    symbol_type=chunk["symbol_metadata"]["symbol_type"],
    symbol_name=chunk["symbol_metadata"]["symbol_name"],
    symbol_signature=chunk["symbol_metadata"]["symbol_signature"],
    parse_status=chunk["symbol_metadata"]["parse_status"],  # NEW
)
```

### Stats Aggregation

Add to `stats.py`:

```python
def get_parse_failure_stats(index_name: str) -> dict[str, dict[str, int]]:
    """Get parse status counts per language.

    Returns:
        {"python": {"ok": 150, "error": 2}, "c": {"ok": 80, "error": 15}}
    """
    table_name = get_table_name(index_name)
    # Check if parse_status column exists (graceful for pre-v1.10)
    # ... same pattern as check_symbol_columns_exist()
```

### Integration with IndexStats

Add `parse_failures: dict[str, dict[str, int]]` to `IndexStats` dataclass. Surface in:
- `index_stats` MCP tool response
- `cocosearch stats --verbose` CLI output
- `/api/stats` HTTP endpoint
- Web dashboard

### Schema Migration

Like the symbol columns (v1.7), use `schema_migration.py` to add `parse_status` column:

```python
def ensure_parse_status_column(conn, table_name: str) -> None:
    """Add parse_status column if missing (v1.10+)."""
    # Same pattern as ensure_symbol_columns()
```

### Risk Assessment

**Low-medium risk.** The main risk is schema migration for existing indexes. The `schema_migration.py` pattern is proven (used for symbol columns in v1.7). Existing rows get NULL for `parse_status`, which stats queries handle with `WHERE parse_status IS NOT NULL`.

---

## Change 5: Default DATABASE_URL

### Problem Statement

Currently, `COCOSEARCH_DATABASE_URL` is required with no default. The Docker image sets it to `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch` internally, but users running natively must set it manually. The `docker-compose.yml` uses different credentials (`cocoindex:cocoindex`).

### Current Usage Points

```
search/db.py: get_connection_pool()
    |
    conninfo = os.getenv("COCOSEARCH_DATABASE_URL")
    if not conninfo:
        raise ValueError("Missing COCOSEARCH_DATABASE_URL")

config/env_validation.py: validate_required_env_vars()
    |
    if not os.getenv("COCOSEARCH_DATABASE_URL"):
        errors.append(EnvVarError(...))

indexer/flow.py: run_index()
    |
    db_url = os.getenv("COCOSEARCH_DATABASE_URL")
    if not db_url:
        raise ValueError("Missing COCOSEARCH_DATABASE_URL")
```

Three separate places read `COCOSEARCH_DATABASE_URL` directly from `os.getenv()`.

### Architecture for Default Value

**Recommended: Single constant, multiple callsites**

Define the default once, reference everywhere:

```python
# In config/__init__.py or a new config/defaults.py
DEFAULT_DATABASE_URL = "postgresql://cocosearch:cocosearch@localhost:5432/cocosearch"
```

Then update all three callsites:
1. `search/db.py:get_connection_pool()` -- `os.getenv("COCOSEARCH_DATABASE_URL", DEFAULT_DATABASE_URL)`
2. `indexer/flow.py:run_index()` -- same pattern
3. `config/env_validation.py:validate_required_env_vars()` -- remove COCOSEARCH_DATABASE_URL from required list (it has a default now)

### Interaction with 4-Level Precedence

The config resolver (`config/resolver.py`) implements: CLI > env > config > default.

For DATABASE_URL specifically:
- **CLI**: Not applicable (no CLI flag for database URL)
- **env**: `COCOSEARCH_DATABASE_URL` env var (overrides default)
- **config**: Not in `cocosearch.yaml` schema (DATABASE_URL is infra config, not project config)
- **default**: `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch`

The default does NOT go through the config resolver because DATABASE_URL is not a config schema field. It is read directly via `os.getenv()` with a fallback default. This is intentional -- database URL is infrastructure configuration, not project configuration.

### docker-compose.yml Alignment

Current `docker-compose.yml` uses `cocoindex:cocoindex`:
```yaml
POSTGRES_USER: cocoindex
POSTGRES_PASSWORD: cocoindex
POSTGRES_DB: cocoindex
```

The default DATABASE_URL uses `cocosearch:cocosearch`. These must be aligned:

```yaml
POSTGRES_USER: cocosearch
POSTGRES_PASSWORD: cocosearch
POSTGRES_DB: cocosearch
```

### Risk Assessment

**Low risk.** The change is additive -- users who already set `COCOSEARCH_DATABASE_URL` see no change. Users who don't set it get a working default that matches the Docker image. The docker-compose credential change requires users to reinitialize their PostgreSQL data directory (or just delete `postgres_data/`).

### Impact on `config check` Command

Currently `cocosearch config check` reports an error if `COCOSEARCH_DATABASE_URL` is not set. After this change, it should:
1. Show the default value with source "default"
2. Not report an error (it has a valid default)
3. Optionally warn that the default assumes local Docker PostgreSQL

---

## Component Boundaries Summary

| Component | Change | Files Touched |
|-----------|--------|---------------|
| Docker image | Strip CocoSearch | `docker/Dockerfile`, `docker/rootfs/` s6 services |
| MCP server | Add Roots support | `mcp/server.py` (tool functions + helper) |
| MCP server | HTTP query params | `mcp/server.py` (middleware/run_server) |
| Indexer | Parse failure tracking | `indexer/symbols.py`, `indexer/flow.py`, `indexer/schema_migration.py` |
| Stats | Parse failure display | `management/stats.py` |
| Config | Default DATABASE_URL | `config/env_validation.py`, `search/db.py`, `indexer/flow.py` |
| Docker Compose | Align credentials | `docker-compose.yml` |

### Cross-Cutting Concerns

Only two component pairs have overlap:
1. **MCP Roots + HTTP Query Params**: Both provide project context to tools. Share the `_detect_project()` helper. Roots is higher priority than query params in the detection chain.
2. **Parse Failure Tracking + Stats**: Parse status column feeds into stats aggregation. Build tracking first, then stats display.

---

## Suggested Build Order

### Phase 1: Foundation Changes (Zero Dependencies)

**1a. Default DATABASE_URL + docker-compose alignment**
- Single constant, update 3 callsites
- Align docker-compose credentials
- Update `config check` behavior
- **Why first:** Unblocks all users who haven't set DATABASE_URL. Removes a common onboarding friction point. Zero risk to existing users.

**1b. Docker simplification (strip CocoSearch)**
- Remove svc-mcp, python-builder stage, init-ready rewire
- Update health-check script
- Update documentation
- **Why alongside 1a:** Independent of all other changes. Purely subtractive.

### Phase 2: Protocol Enhancements (Depend on Phase 1a for testing)

**2a. MCP Roots capability**
- Add `_detect_project()` helper with roots > env > cwd chain
- Make `search_code()` and other tools async
- Handle client without roots gracefully
- **Why second:** Requires the server to be running (Phase 1a default URL helps testing).

**2b. HTTP transport query params**
- Add middleware for `?project=` extraction
- Store in contextvars
- Integrate with `_detect_project()` helper from 2a
- **Why after 2a:** Reuses the same detection helper. Lower priority than Roots.

### Phase 3: Pipeline Observability (Independent)

**3a. Parse failure tracking**
- Add `parse_status` to symbol extraction return
- Add to flow.py `collect()` call
- Schema migration function
- Stats aggregation query
- Surface in IndexStats, CLI, API, dashboard
- **Why last:** Most complex change (touches pipeline + stats + display). Benefits from stable foundation.

### Dependency Diagram

```
Phase 1a: Default DATABASE_URL ----+
                                   |
Phase 1b: Docker simplification    |  (parallel, independent)
                                   |
Phase 2a: MCP Roots ---------------+---> shares _detect_project()
                                   |
Phase 2b: HTTP Query Params -------+

Phase 3a: Parse Failure Tracking      (independent of all above)
```

---

## Patterns to Follow

### Pattern: Graceful Feature Detection (Schema Evolution)

Used throughout CocoSearch for schema evolution. Apply to parse_status:

```python
# Check if parse_status column exists before querying
col_check = """
    SELECT column_name FROM information_schema.columns
    WHERE table_name = %s AND column_name = 'parse_status'
"""
# If not present: skip parse failure stats (pre-v1.10 index)
```

### Pattern: Additive Schema Migration

Never alter existing columns. Only add new ones:
```python
def ensure_parse_status_column(conn, table_name):
    """Add parse_status column if missing. Idempotent."""
    conn.execute(f"""
        ALTER TABLE {table_name}
        ADD COLUMN IF NOT EXISTS parse_status TEXT
    """)
```

### Pattern: Transport-Agnostic Detection

Keep `find_project_root()` in `management/context.py` transport-agnostic. MCP-specific detection (roots, query params) stays in `mcp/server.py`:

```
management/context.py: find_project_root()    -- filesystem only, no MCP dependency
mcp/server.py: _detect_project(ctx)           -- roots > query_param > env > cwd
```

### Pattern: Fallback Chain with Source Tracking

Every detection method should return what detected the project, for logging and debugging:

```python
async def _detect_project(ctx) -> tuple[Path | None, str | None]:
    # Returns (path, "roots") or (path, "query_param") or (path, "env") or (path, "git")
```

## Anti-Patterns to Avoid

### Anti-Pattern: Global State for Per-Session Data

Do NOT store HTTP query param project path in a module-level variable:
```python
# BAD: Race condition with multiple HTTP sessions
_current_project = None

@mcp.tool()
def search_code(...):
    if _current_project: ...
```

Use `contextvars.ContextVar` instead for async-safe per-request state.

### Anti-Pattern: Breaking the Existing Detection Chain

Do NOT remove cwd-based detection when adding Roots:
```python
# BAD: Roots-only, breaks stdio without client roots support
root_path = await ctx.session.list_roots()
if not root_path:
    raise Error("No roots")  # Wrong -- should fallback to cwd
```

Always maintain the fallback chain: roots > env > cwd.

### Anti-Pattern: Tracking Failures Outside the Pipeline

Do NOT try to maintain external counters for parse failures:
```python
# BAD: CocoIndex transforms run in Rust pipeline, can't reliably share Python state
_failure_count = 0  # Unreliable across pipeline stages

@cocoindex.op.function()
def extract_symbol_metadata(...):
    global _failure_count
    _failure_count += 1  # May not work in parallel execution
```

Store status in the output schema where CocoIndex manages the data flow.

---

## Scalability Considerations

| Concern | Current (v1.9) | After v1.10 |
|---------|----------------|-------------|
| Project detection latency | ~1ms (filesystem walk) | ~5ms (roots RPC + fallback) |
| Schema columns per row | 11 | 12 (+ parse_status) |
| Docker image size | ~3.5GB (PG + Ollama + Python) | ~3.0GB (PG + Ollama only) |
| Config setup steps | 2 (set DATABASE_URL + start Docker) | 1 (start Docker, URL defaults) |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Docker stripping | HIGH | Pure deletion, verified s6-overlay dependency structure in `rootfs/` |
| MCP Roots integration | HIGH | MCP spec verified at spec URL, FastMCP Context API confirmed at docs |
| HTTP query params | MEDIUM | Starlette middleware is standard, but FastMCP's internal ASGI wiring needs verification |
| Parse failure tracking | HIGH | Same schema migration pattern as v1.7 symbols, proven approach |
| Default DATABASE_URL | HIGH | Simple `os.getenv()` with default, verified all 3 callsites |
| Build order | HIGH | Dependencies mapped from code analysis, no circular dependencies |

## Sources

### Official Documentation
- [MCP Roots Specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/client/roots) -- Protocol-level roots capability
- [MCP Transports Specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) -- Streamable HTTP session management
- [FastMCP Context Documentation](https://gofastmcp.com/python-sdk/fastmcp-server-context) -- `ctx.session.list_roots()` API
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) -- Official SDK repository

### Codebase (Primary Sources)
- `src/cocosearch/mcp/server.py` -- FastMCP server, tool definitions, project detection
- `src/cocosearch/management/context.py` -- `find_project_root()`, `resolve_index_name()`
- `src/cocosearch/search/db.py` -- `get_connection_pool()`, `COCOSEARCH_DATABASE_URL` usage
- `src/cocosearch/indexer/flow.py` -- CocoIndex pipeline, `run_index()`
- `src/cocosearch/indexer/symbols.py` -- Symbol extraction with error handling
- `src/cocosearch/config/env_validation.py` -- Required env var validation
- `docker/Dockerfile` -- All-in-one image with s6-overlay services
- `docker/rootfs/` -- s6-overlay service definitions and scripts

### Prior Research
- `.planning/research/ARCHITECTURE-v1.9-multi-repo.md` -- Existing project detection architecture
- `.planning/research/ARCHITECTURE-ALLINONE.md` -- Docker all-in-one design decisions

---
*Researched: 2026-02-08*
