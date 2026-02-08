# Feature Landscape: CocoSearch v1.10

**Domain:** MCP protocol compliance, HTTP transport context, parse observability, Docker simplification
**Researched:** 2026-02-08
**Research mode:** Ecosystem (features dimension)

## Executive Summary

This research covers five feature areas for v1.10: MCP Roots capability, HTTP transport project context, parse failure tracking, infra-only Docker images, and sensible database defaults. These range from protocol compliance work (Roots) to developer experience improvements (Docker, defaults). The MCP Roots capability is the highest-value feature because it replaces the current `--project-from-cwd` workaround with protocol-correct project detection that works across all MCP clients.

---

## Feature 1: MCP Roots Capability

### What It Is

MCP Roots is a client-to-server mechanism defined in the MCP specification (2025-11-25) where the client advertises which filesystem directories (as `file://` URIs) the server is allowed to operate within. The server can request this list via `roots/list` and receive change notifications via `notifications/roots/list_changed`.

**Source:** [MCP Specification - Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots) (HIGH confidence)

### How It Works in the Protocol

1. **Client declares capability** during initialization:
   ```json
   {
     "capabilities": {
       "roots": {
         "listChanged": true
       }
     }
   }
   ```

2. **Server requests roots** via JSON-RPC:
   ```json
   {"jsonrpc": "2.0", "id": 1, "method": "roots/list"}
   ```

3. **Client responds** with root list:
   ```json
   {
     "roots": [
       {
         "uri": "file:///home/user/projects/myproject",
         "name": "My Project"
       }
     ]
   }
   ```

4. **Client notifies on change** via `notifications/roots/list_changed`, after which the server should re-request roots.

### How It Applies to CocoSearch

CocoSearch currently uses `COCOSEARCH_PROJECT_PATH` environment variable set by the `--project-from-cwd` CLI flag. This is a workaround because:
- It captures `os.getcwd()` at server launch time, which is fixed for the session
- It does not respond to workspace changes in the client
- It is non-standard -- clients must configure the flag in their MCP server launch command

With Roots support, CocoSearch would:
1. Request roots from the client when `search_code` is called without an explicit `index_name`
2. Use the first root's `file://` URI as the project path for auto-detection
3. Fall back to existing `COCOSEARCH_PROJECT_PATH` or `os.getcwd()` when roots are not available
4. Optionally listen for `roots/list_changed` to invalidate cached project detection

### Python MCP SDK Support

The official `mcp` Python SDK (currently used at `>=1.26.0`) provides roots access through the `Context` object in FastMCP:

```python
from mcp.server.fastmcp import FastMCP, Context

@mcp.tool()
async def search_code(query: str, ctx: Context) -> list[dict]:
    roots = await ctx.list_roots()
    if roots:
        project_path = roots[0].uri  # file:///path/to/project
        # ... use for auto-detection
```

**Source:** [FastMCP Context docs](https://gofastmcp.com/python-sdk/fastmcp-server-context) (MEDIUM confidence)

**Important caveat:** `list_roots()` returns `ErrorData` with `INVALID_REQUEST` when the client does not support roots. The implementation must handle this gracefully.

### Client Support Status

| Client | Roots Support | Notes |
|--------|---------------|-------|
| Claude Desktop | Yes | Sends workspace directories via roots, recently rewritten to support roots |
| Claude Code | Yes | Sends working directory as root |
| Cursor | Unclear | May not advertise roots capability |
| VS Code Copilot | Unclear | MCP support is newer |
| Custom clients | Varies | Depends on implementation |

**Confidence:** MEDIUM -- Claude Desktop/Code support verified via search results, other clients unverified.

### Impact on Current Code

Current auto-detection in `search_code()` (lines 213-277 of `server.py`):
- Checks `COCOSEARCH_PROJECT_PATH` env var first
- Falls back to `find_project_root()` from `management/context.py`
- Walks up directory tree looking for `.git` or `cocosearch.yaml`

With Roots, this becomes a 4-tier fallback:
1. Explicit `index_name` parameter (already exists)
2. **MCP Roots** -- query client for workspace roots (NEW)
3. `COCOSEARCH_PROJECT_PATH` env var (existing)
4. `find_project_root()` from cwd (existing)

### Classification: TABLE STAKES

Roots is part of the MCP specification. Any MCP server that does project/workspace detection should use Roots when available. The current `--project-from-cwd` workaround is fragile and non-standard. This is a protocol compliance feature.

### Complexity: MEDIUM

- Requires making `search_code` async (or using the Context's async API)
- Must handle clients that do not support roots gracefully
- Must parse `file://` URIs to filesystem paths
- Must handle multiple roots (multi-repo scenario)
- Should integrate with existing `find_project_root()` logic

---

## Feature 2: HTTP Transport Project Context via Query Params

### What It Is

When CocoSearch runs as an HTTP (Streamable HTTP) server, the MCP endpoint is a single URL (e.g., `http://localhost:3000/mcp`). Currently there is no way for a client connecting over HTTP to indicate which project it is working with, other than passing `index_name` explicitly in every tool call.

The proposal is to accept project context via a URL query parameter, so clients can connect to `http://localhost:3000/mcp?project=/path/to/myproject` and have all tool calls scoped to that project.

### How It Works in the MCP Spec

The MCP spec defines the Streamable HTTP endpoint as "a single HTTP endpoint path" (e.g., `https://example.com/mcp`). The spec does not explicitly address query parameters on the endpoint URL. However:

- The spec allows servers to use any URL path as the MCP endpoint
- Query parameters on the endpoint URL are not prohibited
- Session management already uses the `MCP-Session-Id` header to scope sessions

**Source:** [MCP Specification - Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) (HIGH confidence)

### Design Considerations

**Option A: Query parameter on MCP endpoint URL**
- Client connects to `http://host:3000/mcp?project=/path/to/project`
- Server extracts `project` query param during initialization
- Scopes the session to that project
- Pro: Simple, stateless discovery
- Con: Non-standard -- MCP clients may not support adding query params to server URLs

**Option B: Pass project in `InitializeRequest` params**
- Use MCP's initialization parameters to pass project context
- More protocol-aligned but requires client cooperation
- Con: Most MCP clients do not support custom init params

**Option C: Rely on Roots (preferred for most cases)**
- HTTP clients that support Roots can advertise project directories via the Roots capability
- This is the protocol-correct approach
- The query param becomes a fallback for clients that lack Roots support

### Recommended Approach

The query parameter approach is useful as a **secondary mechanism** for HTTP transport when:
- The client does not support MCP Roots
- The server is shared by multiple projects (e.g., Docker deployment)
- Quick testing or curl-based integration

Implementation: Extract `project` query param from the initial HTTP request URL and store it in the session context. Use it as the fallback before `COCOSEARCH_PROJECT_PATH` in the detection chain.

### Classification: DIFFERENTIATOR

This is not a standard MCP pattern -- it is a CocoSearch-specific convenience for HTTP deployments. Useful but not expected. The primary mechanism for project detection should be Roots.

### Complexity: LOW-MEDIUM

- Extract query params from the Starlette request during MCP initialization
- Store in session-scoped state
- Wire into the existing project detection fallback chain
- The main challenge is accessing the HTTP request context within MCP tool handlers

---

## Feature 3: Parse Failure Tracking and Reporting

### What It Is

CocoSearch uses tree-sitter to parse source code during indexing for:
1. **Chunking** -- `SplitRecursively` uses tree-sitter for semantic code splitting
2. **Symbol extraction** -- `extract_symbol_metadata` parses chunks to find functions/classes

Currently, parse failures are silently swallowed. The `extract_symbol_metadata` function catches all exceptions and returns NULL fields (lines 446-453 of `symbols.py`). There is no tracking of:
- How many files had parse errors
- Which languages have high failure rates
- Whether failures are due to tree-sitter grammar limitations or genuinely broken code

### How Tree-Sitter Reports Errors

Tree-sitter does not fail on parse errors. Instead, it produces a parse tree with special error nodes:

| Node Property | What It Detects |
|---------------|-----------------|
| `node.has_error` | True if this node OR any descendant contains a syntax error |
| `node.is_error` | True if this specific node represents a syntax error (ERROR node) |
| `node.is_missing` | True if this node was inserted by the parser to recover from an error (MISSING node) |
| `tree.root_node.has_error` | Quick check: does the entire parse tree contain any errors? |

**Source:** [py-tree-sitter Node API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Node.html) (HIGH confidence)

To detect parse failures, check `tree.root_node.has_error` after parsing. To count error nodes, traverse the tree and count nodes where `is_error` or `is_missing` is True.

### What to Track

**Per-file metrics during indexing:**
- `has_errors: bool` -- did the parse tree contain any errors?
- `error_count: int` -- number of ERROR nodes in the parse tree
- `missing_count: int` -- number of MISSING nodes

**Aggregate metrics in index stats:**
- `parse_failures_by_language: dict[str, int]` -- count of files with parse errors per language
- `total_files_with_errors: int` -- across all languages
- `parse_success_rate: float` -- percentage of files that parsed cleanly

### Where to Integrate

1. **Symbol extraction** (`symbols.py`): After `parser.parse()`, check `tree.root_node.has_error`. If true, log and count. The symbol extraction already runs per-chunk, so this adds minimal overhead.

2. **Index stats** (`stats.py` / `get_comprehensive_stats`): Add parse failure counts to the stats output. This requires storing parse results somewhere -- either:
   - **Option A:** Add columns to the chunks table (simple but schema change)
   - **Option B:** Aggregate at indexing time and store in metadata table (cleaner)
   - **Option C:** Log-based tracking with structured logging (simplest, no schema change)

3. **Stats CLI and MCP output**: Surface parse failure stats in `cocosearch stats` output and `index_stats` MCP tool.

### Classification: TABLE STAKES

For a code search tool that uses tree-sitter parsing, tracking parse failures is essential observability. Users need to know if their code is being indexed correctly. Without this, users have no way to diagnose "why didn't search find my function?" when the answer is "tree-sitter couldn't parse that file."

This was already flagged in STATE.md: "Consider parse failure tracking in stats output (per-language counts)"

### Complexity: LOW-MEDIUM

- Tree-sitter already produces parse trees; checking `has_error` is trivial
- The main complexity is deciding where to store and aggregate the data
- Simplest viable approach: structured logging during indexing + summary counts in stats
- More robust approach: store per-chunk parse status in a metadata column

---

## Feature 4: Docker Infra-Only Images

### What It Is

The current Docker image (`docker/Dockerfile`) bundles everything into a single container:
- PostgreSQL 16 + pgvector
- Ollama + pre-baked nomic-embed-text model
- CocoSearch Python application + MCP server
- s6-overlay for process supervision

This all-in-one approach has trade-offs:
- **Pro:** Single `docker run` command, zero configuration
- **Con:** Large image (~4GB+), couples application to infrastructure, hard to upgrade components independently, cannot use host-installed Ollama

The proposal is to offer a **infra-only Docker image** that provides just the backend services (PostgreSQL + pgvector, Ollama) without bundling CocoSearch itself. Users would run CocoSearch natively (via `pip install` or `uv`) and point it at the Docker-provided infrastructure.

### How This Pattern Works

**Docker Compose approach (infra only):**

The existing `docker-compose.yml` already follows this pattern -- it defines only `db` (pgvector) and `ollama` services without a CocoSearch service. Users run CocoSearch on their host machine.

```yaml
# Current docker-compose.yml (already infra-only)
services:
  db:
    image: pgvector/pgvector:pg17
    ports:
      - "5432:5432"
    # ...
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    # ...
```

**Source:** Project's existing `docker-compose.yml` (HIGH confidence)

The infra-only pattern means:
1. Docker provides databases and models
2. Application runs on the host (better for development, debugging, and MCP stdio transport)
3. Application connects to Docker services via `localhost:5432` and `localhost:11434`

### What Needs to Change

The `docker-compose.yml` already provides infra-only services. What is missing:

1. **Documentation** -- Clear guidance on "use docker-compose.yml for infra, install CocoSearch natively"
2. **Sensible defaults** -- Environment variables that "just work" with the Docker infra (see Feature 5)
3. **Health check coordination** -- Scripts or docs for waiting until Docker services are ready before running CocoSearch
4. **Model auto-pull** -- The Ollama service in docker-compose.yml already pulls `nomic-embed-text` at startup, but this takes 60+ seconds. Clear feedback to users is needed.
5. **Optional: A dedicated `docker-compose.infra.yml`** -- A separate compose file explicitly named for infra-only use, with comments explaining the pattern

### Relationship to All-in-One Image

The all-in-one image (`docker/Dockerfile`) should remain as an option for users who want zero-config deployment. The infra-only compose is the recommended path for development and MCP stdio usage.

| Use Case | Recommendation |
|----------|---------------|
| Quick demo / evaluation | All-in-one Docker image |
| Development with MCP stdio | Infra-only compose + native CocoSearch |
| Production / shared server | Infra-only compose + native CocoSearch as systemd service |
| CI/CD testing | Infra-only compose (already used in test infrastructure) |

### Classification: TABLE STAKES

The docker-compose.yml already exists and works. This feature is about making it a first-class documented path rather than an afterthought. Users who install CocoSearch via pip and want to avoid manual PostgreSQL/Ollama setup need a clear "just run docker compose up" path.

### Complexity: LOW

- The infrastructure already exists in `docker-compose.yml`
- Main work is documentation, defaults, and possibly a dedicated compose file
- No code changes to CocoSearch itself needed (beyond default connection strings)

---

## Feature 5: Sensible Defaults for Database Connection Strings

### What It Is

Currently, `COCOSEARCH_DATABASE_URL` is a required environment variable with no default. If unset, CocoSearch fails with:
```
Missing COCOSEARCH_DATABASE_URL environment variable
```

The proposal is to provide sensible defaults that match the Docker infrastructure setup, so that `docker compose up && cocosearch index .` works without any environment variable configuration.

### PostgreSQL Connection String Conventions

Standard PostgreSQL connection string format:
```
postgresql://[user[:password]@][host][:port][/dbname]
```

PostgreSQL defaults (from libpq):
- **Host:** localhost (or Unix socket)
- **Port:** 5432
- **User:** current OS user (or `postgres`)
- **Database:** same as user
- **Password:** none (trust auth for localhost)

**Source:** [PostgreSQL documentation](https://www.postgresql.org/docs/current/libpq-connect.html) (HIGH confidence)

### Current State in CocoSearch

| Context | Database URL | User/DB |
|---------|-------------|---------|
| All-in-one Docker | `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch` | cocosearch/cocosearch |
| docker-compose.yml | `postgresql://cocoindex:cocoindex@localhost:5432/cocoindex` | cocoindex/cocoindex |
| User-configured | Whatever `COCOSEARCH_DATABASE_URL` is set to | varies |

There is a mismatch: the all-in-one Docker image uses `cocosearch` user/db while `docker-compose.yml` uses `cocoindex` user/db.

### Recommended Default

The sensible default should match the `docker-compose.yml` since that is the infra-only setup users will use:

```
postgresql://cocoindex:cocoindex@localhost:5432/cocoindex
```

**Rationale:**
- Matches the existing docker-compose.yml without changes
- Uses `cocoindex` which aligns with the CocoIndex library naming
- `localhost:5432` matches PostgreSQL default port
- Simple credentials acceptable for local development tool

**Fallback chain:**
1. `COCOSEARCH_DATABASE_URL` environment variable (explicit override)
2. Default: `postgresql://cocoindex:cocoindex@localhost:5432/cocoindex`

### Implementation

In the config loading or CocoIndex initialization:

```python
db_url = os.getenv(
    "COCOSEARCH_DATABASE_URL",
    "postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
)
```

This change should propagate to:
- `flow.py` line 199: `os.getenv("COCOSEARCH_DATABASE_URL")`
- CocoIndex initialization (which also reads this env var)
- `config check` command validation

### Ollama Default

Ollama already has a sensible default -- `http://localhost:11434` is the standard Ollama URL and is the default in most embedding libraries. CocoSearch's `COCOSEARCH_OLLAMA_URL` already defaults to this when unset.

### Classification: TABLE STAKES

For a local-first developer tool, requiring manual environment variable configuration before first use creates unnecessary friction. Sensible defaults that work with the standard Docker infra are expected.

### Complexity: LOW

- Single default value change
- Must verify CocoIndex library also accepts this default (or passes it through)
- Should update `config check` to handle the default gracefully
- Must align docker-compose.yml credentials if they differ

---

## Table Stakes (Must Have)

Features users expect. Missing = product feels incomplete or protocol-incorrect.

| Feature | Why Expected | Complexity | Priority |
|---------|--------------|------------|----------|
| MCP Roots capability | Protocol-correct project detection; replaces fragile `--project-from-cwd` workaround | Medium | P0 |
| Parse failure tracking | Essential observability for a code search tool using tree-sitter | Low-Medium | P1 |
| Sensible database defaults | Local-first tool should work with `docker compose up && cocosearch index .` | Low | P1 |
| Infra-only Docker docs | docker-compose.yml exists but is not documented as first-class path | Low | P2 |

## Differentiators

Features that set the product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Priority |
|---------|-------------------|------------|----------|
| HTTP query param project context | Enables multi-project HTTP deployments without per-call `index_name` | Low-Medium | P2 |
| Multi-root project support | Handle workspaces with multiple project roots via MCP Roots | Medium | P3 |
| Per-language parse failure stats in CLI | Rich stats output showing parse success rates by language | Low | P3 |

## Anti-Features

Features to explicitly NOT build for v1.10.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Roots-based filesystem access control | MCP Roots defines boundaries but CocoSearch does not access arbitrary files -- it only reads indexed data. Implementing filesystem sandboxing is unnecessary scope. | Respect roots for project detection only, not as a security boundary. |
| Custom MCP transport for project context | Building a custom transport layer to pass project context adds complexity with no standard benefit. | Use query params on the standard Streamable HTTP endpoint. |
| Re-building Docker image without all-in-one | Do not remove the all-in-one image; it serves the quick-start use case. | Offer infra-only compose as an alternative, not a replacement. |
| Parse failure auto-remediation | Do not attempt to fix or work around tree-sitter parse errors automatically (e.g., falling back to regex parsing). | Track and report failures; let users investigate. |
| OAuth/auth on HTTP transport | Authentication for the HTTP MCP endpoint is not needed for a local-first tool. | Bind to localhost by default; users who expose publicly should handle auth at the reverse proxy level. |

## Feature Dependencies

```
Sensible Defaults ──> Infra-Only Docker (defaults must match compose)
                  └──> Parse Tracking (stats need working DB connection)

MCP Roots ──> HTTP Query Param (Roots is primary, query param is fallback)
         └──> Multi-Root Support (multi-root is an extension of basic Roots)

Parse Tracking ──> Stats CLI Output (tracking data surfaces through stats)
```

**Ordering rationale:**
1. Sensible defaults should come first because they enable the infra-only Docker path and reduce friction for all other features.
2. MCP Roots is the core protocol feature and should be implemented before the HTTP query param fallback.
3. Parse failure tracking can be done independently but benefits from a working default setup.

## MVP Recommendation

For v1.10 MVP, prioritize:

1. **Sensible database defaults** -- Lowest effort, highest friction reduction. Changes one line of code plus documentation. Enables "just works" experience with Docker infra.
2. **MCP Roots capability** -- Protocol compliance. Replaces the `--project-from-cwd` workaround with the standard mechanism. Makes CocoSearch work correctly in Claude Desktop and Claude Code without special configuration.
3. **Parse failure tracking** -- Observability table stakes. Check `tree.root_node.has_error` after parsing, aggregate counts, surface in stats output.

Defer to post-v1.10:
- **HTTP query param project context**: Useful but lower priority since Roots handles the primary use case. Can be added when HTTP multi-project deployments become common.
- **Multi-root support**: Extension of Roots. The basic implementation (use first root) is sufficient for v1.10.
- **Per-language parse stats breakdown**: Nice to have in stats output but not blocking.

## Implementation Notes

### MCP Roots: Key Technical Decisions

1. **Sync vs async**: Current `search_code` is synchronous. `ctx.list_roots()` is async. Options:
   - Make `search_code` async (preferred -- FastMCP supports async tools)
   - Use `asyncio.run()` wrapper (not recommended inside async server)

2. **URI parsing**: Roots return `file:///path/to/project` URIs. Use `urllib.parse.urlparse()` to extract the filesystem path. Handle platform differences (Windows vs Unix paths).

3. **Graceful degradation**: When client does not support roots, `list_roots()` raises an error. Catch and fall through to existing detection methods.

4. **Caching**: Cache roots per-session rather than per-call. Listen for `notifications/roots/list_changed` to invalidate.

### Parse Tracking: Storage Decision

| Approach | Pros | Cons |
|----------|------|------|
| Structured logging only | No schema change, simplest | Stats not queryable, lost on log rotation |
| Metadata table column | Queryable, survives restarts | Schema migration needed |
| In-memory aggregation during indexing | Simple, immediate | Lost after indexing completes |
| Summary stored in index metadata | Queryable, no per-chunk overhead | Requires metadata table update |

**Recommendation:** Store summary counts in index metadata (the same metadata table used for path registration). During indexing, aggregate in-memory, then write summary after indexing completes. This avoids schema changes to the chunks table and provides queryable stats.

### Database Defaults: Alignment Check

The docker-compose.yml credentials and the default connection string must match:

```yaml
# docker-compose.yml
POSTGRES_USER: cocoindex
POSTGRES_PASSWORD: cocoindex
POSTGRES_DB: cocoindex
```

Default: `postgresql://cocoindex:cocoindex@localhost:5432/cocoindex`

These already align. The all-in-one Docker image uses different credentials (`cocosearch:cocosearch`), but that image sets `COCOSEARCH_DATABASE_URL` explicitly so the default is irrelevant there.

## Sources

### HIGH Confidence (Official documentation, verified)

- [MCP Specification 2025-11-25 - Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [MCP Specification 2025-11-25 - Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [py-tree-sitter Node API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Node.html)
- [PostgreSQL Connection Docs](https://www.postgresql.org/docs/current/libpq-connect.html)
- Project source code: `src/cocosearch/mcp/server.py`, `src/cocosearch/management/context.py`, `src/cocosearch/indexer/symbols.py`

### MEDIUM Confidence (Multiple sources agree, partially verified)

- [FastMCP Context - list_roots()](https://gofastmcp.com/python-sdk/fastmcp-server-context)
- [Claude Desktop roots support](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
- [tree-sitter ERROR/MISSING nodes](https://github.com/tree-sitter/tree-sitter/issues/1136)
- [Docker Compose infra patterns](https://docs.docker.com/compose/)

### LOW Confidence (Single source, unverified)

- Claude Code roots support (mentioned in search results but not officially documented for this specific behavior)
- Cursor/VS Code MCP roots support status (unclear from available sources)
- FastMCP 2.0 vs 3.0 roots API stability (active development may change APIs)
