# Phase 45: MCP Protocol Enhancements - Research

**Researched:** 2026-02-08
**Domain:** MCP SDK (mcp v1.26.0), FastMCP, Starlette ASGI, file:// URI handling
**Confidence:** HIGH

## Summary

This phase adds MCP Roots capability for protocol-correct project detection, an HTTP `project_path` query parameter for HTTP transports, and Streamable HTTP transport support. Research was conducted by directly inspecting the installed MCP SDK v1.26.0 source code, verifying API signatures, type structures, and transport internals.

The installed `mcp` package (v1.26.0) includes FastMCP as `mcp.server.fastmcp`. It provides full support for Roots via `ServerSession.list_roots()`, Streamable HTTP transport via `mcp.run(transport="streamable-http")`, and the Starlette `Request` object is available inside tool handlers via `ctx.request_context.request`. The existing codebase already supports the `streamable-http` transport (the `run_server` function handles `transport="http"` by calling `mcp.run(transport="streamable-http")`), so this phase primarily adds Roots and query param capabilities while making tools async and Context-aware.

**Primary recommendation:** Convert tool functions to async, add a `ctx: Context` parameter for session access, and implement `_detect_project()` as a shared async helper that follows the roots > query_param > env > cwd priority chain.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 1.26.0 | MCP Python SDK with FastMCP | Already installed; includes server, types, transports |
| `starlette` | (bundled) | ASGI framework for HTTP transports | Used by MCP SDK internally, already a dependency |
| `pydantic` | (bundled) | Data validation, `FileUrl` type | Used by MCP types for Root.uri |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.parse` | stdlib | Parse file:// URIs | `urlparse()` + `unquote()` for URI-to-path |
| `pathlib` | stdlib | Filesystem path handling | `Path(decoded_path)` for validation |
| `contextvars` | stdlib | Per-request state (ContextVar) | Optional: for query param propagation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `urlparse` for file:// | `FileUrl.path` (Pydantic) | `FileUrl.path` does NOT decode percent-encoding; `urlparse` + `unquote` handles `%20` etc. correctly |
| ContextVar for query params | Direct Request access | Request is already available via `ctx.request_context.request`; ContextVar adds complexity for no benefit |

**Installation:**
No new packages needed. All functionality is available in `mcp==1.26.0` and Python stdlib.

## Architecture Patterns

### Recommended Project Structure
```
src/cocosearch/mcp/
  __init__.py          # (existing) exports mcp, run_server
  server.py            # (existing) FastMCP instance, tools, run_server
  project_detection.py # (NEW) _detect_project() helper, file_uri_to_path()
```

### Pattern 1: Context Injection for Async Tools
**What:** FastMCP auto-injects a `Context` object into tool functions that declare a parameter with the `Context` type annotation. The parameter name is flexible (e.g., `ctx`, `context`).
**When to use:** Any tool that needs to call `list_roots()` or access the HTTP request.
**Example:**
```python
# Source: mcp v1.26.0 mcp/server/fastmcp/server.py lines 456-486
from mcp.server.fastmcp import Context

@mcp.tool()
async def search_code(
    query: Annotated[str, Field(description="...")],
    ctx: Context,  # Auto-injected by FastMCP
) -> list[dict]:
    # ctx.session gives ServerSession
    # ctx.request_context.request gives Starlette Request (HTTP only, None for stdio)
    project_path = await _detect_project(ctx)
    ...
```

### Pattern 2: Roots Capability Access
**What:** `ctx.session.list_roots()` sends a `roots/list` request to the client and returns `ListRootsResult` containing `roots: list[Root]`. Each `Root` has `uri: FileUrl` and `name: str | None`.
**When to use:** First step in the project detection priority chain.
**Example:**
```python
# Source: mcp v1.26.0 mcp/server/session.py lines 350-355
from mcp.types import ClientCapabilities, RootsCapability, Root
from mcp.shared.exceptions import McpError

async def _try_roots(ctx: Context) -> Path | None:
    """Try to get project path from MCP Roots capability."""
    session = ctx.session
    # Check if client declared roots capability
    if not session.check_client_capability(
        ClientCapabilities(roots=RootsCapability())
    ):
        return None
    try:
        result = await session.list_roots()  # Returns ListRootsResult
        for root in result.roots:
            path = file_uri_to_path(str(root.uri))
            if path and path.exists():
                return path
        return None
    except McpError:
        return None
```

### Pattern 3: HTTP Query Parameter Access
**What:** Both SSE and Streamable HTTP transports store the Starlette `Request` object in `ServerMessageMetadata.request_context`, which propagates to `RequestContext.request`. In tool handlers, access via `ctx.request_context.request`.
**When to use:** Reading `?project_path=` from HTTP requests.
**Example:**
```python
# Source: mcp v1.26.0
# - mcp/server/sse.py line 244: metadata = ServerMessageMetadata(request_context=request)
# - mcp/server/streamable_http.py line 637: session_message = self._create_session_message(message, request, ...)
# - mcp/server/lowlevel/server.py line 758: request=request_data (from metadata.request_context)

def _try_query_param(ctx: Context) -> Path | None:
    """Try to get project path from HTTP query parameter."""
    request = ctx.request_context.request  # Starlette Request or None
    if request is None:
        return None
    project_path = request.query_params.get("project_path")
    if not project_path:
        return None
    path = Path(project_path)
    if not path.is_absolute():
        return None  # Reject relative paths
    return path if path.exists() else None
```

### Pattern 4: file:// URI to Path Conversion
**What:** Convert `file:///path/to/dir` to `/path/to/dir` using `urlparse` + `unquote`.
**When to use:** Processing Root.uri values.
**Example:**
```python
from urllib.parse import urlparse, unquote
from pathlib import Path

def file_uri_to_path(uri: str) -> Path | None:
    """Convert a file:// URI to a filesystem Path (Unix only)."""
    if not uri.startswith("file://"):
        return None
    parsed = urlparse(uri)
    decoded_path = unquote(parsed.path)
    if not decoded_path:
        return None
    return Path(decoded_path)
```

**Critical note:** Do NOT use `FileUrl.path` from Pydantic -- it does NOT decode percent-encoding. For example, `FileUrl("file:///my%20project").path` returns `"/my%20project"` (not decoded), while `urlparse` + `unquote` correctly returns `"/my project"`.

### Pattern 5: Roots Change Notification Handling
**What:** Register a handler for `notifications/roots/list_changed` on the low-level MCP server so the project detection cache can be invalidated.
**When to use:** When implementing dynamic re-detection as roots change mid-session.
**Example:**
```python
# Source: mcp v1.26.0 mcp/server/lowlevel/server.py line 159
# notification_handlers is a dict[type, Callable[..., Awaitable[None]]]
from mcp.types import RootsListChangedNotification

# Register on the underlying low-level server:
mcp._mcp_server.notification_handlers[RootsListChangedNotification] = handle_roots_changed
```
**Note:** FastMCP does NOT expose a decorator for notification handlers. You must register directly on `mcp._mcp_server.notification_handlers`.

### Anti-Patterns to Avoid
- **Blocking tools with roots access:** `list_roots()` is async -- tools MUST be async to call it. Sync tool functions cannot use `await`.
- **Using `FileUrl.path` for URI decoding:** Returns percent-encoded string, not decoded filesystem path. Always use `urlparse` + `unquote`.
- **Assuming `ctx.request_context.request` is always available:** It is `None` for stdio transport. Always check before accessing `query_params`.
- **Declaring Roots in ServerCapabilities:** The server does NOT need to declare roots support -- roots is a CLIENT capability. The server simply calls `session.list_roots()` when the client reports having the capability. `ServerCapabilities` has no `roots` field.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| file:// URI parsing | Custom string slicing | `urlparse()` + `unquote()` | Handles percent-encoding, edge cases |
| Checking client supports roots | Inspecting raw client params | `session.check_client_capability(ClientCapabilities(roots=RootsCapability()))` | Handles None checks, nested capability matching |
| Streamable HTTP transport | Custom ASGI app | `mcp.run(transport="streamable-http")` | Already implemented and working in codebase |
| Context injection | Manual parameter passing | FastMCP auto-injection via `ctx: Context` type hint | Framework handles it; parameter name is flexible |

**Key insight:** The MCP SDK already handles transport-level complexity (session management, message routing, SSE streaming). The phase work is purely at the tool-handler level -- adding Context access and implementing the detection priority chain.

## Common Pitfalls

### Pitfall 1: Sync-to-Async Tool Conversion
**What goes wrong:** Current tools are sync functions (e.g., `def search_code(...)`). Adding `ctx: Context` and calling `await ctx.session.list_roots()` requires the tool to be `async def`.
**Why it happens:** FastMCP supports both sync and async tools, but async operations (like roots) require async functions.
**How to avoid:** Convert all tools that need roots/context to `async def`. FastMCP handles both transparently -- the `@mcp.tool()` decorator works the same.
**Warning signs:** `RuntimeError: cannot await in sync function` or `coroutine was never awaited`.

### Pitfall 2: Accessing Request in stdio Transport
**What goes wrong:** `ctx.request_context.request` is `None` for stdio transport because there's no HTTP request.
**Why it happens:** Only SSE and Streamable HTTP transports set `ServerMessageMetadata.request_context` to a Starlette Request object.
**How to avoid:** Always guard with `if ctx.request_context.request is not None` before accessing `query_params`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'query_params'`.

### Pitfall 3: McpError When Client Doesn't Support Roots
**What goes wrong:** Calling `session.list_roots()` when the client doesn't support roots raises `McpError` (the request is sent but the client responds with an error).
**Why it happens:** `list_roots()` sends a `roots/list` JSON-RPC request. If the client hasn't declared roots capability, it may reject the request.
**How to avoid:** Always check `session.check_client_capability(ClientCapabilities(roots=RootsCapability()))` BEFORE calling `list_roots()`. Also wrap in try/except McpError as a safety net.
**Warning signs:** Unhandled `McpError` exceptions in tool handlers.

### Pitfall 4: Accessing _mcp_server for Notification Registration
**What goes wrong:** FastMCP doesn't expose a public API for registering notification handlers. Using `mcp._mcp_server.notification_handlers` works but accesses a private attribute.
**Why it happens:** The low-level Server has `notification_handlers` dict, but FastMCP doesn't wrap this.
**How to avoid:** Accept the private attribute access -- it's stable in v1.26.0 and the standard pattern. Document it clearly for future SDK upgrades.
**Warning signs:** Attribute name changes in future MCP SDK versions.

### Pitfall 5: Shared /mcp Endpoint for SSE and Streamable HTTP
**What goes wrong:** The CONTEXT.md mentions "shared /mcp endpoint handles both SSE and Streamable HTTP." However, FastMCP's `sse_app()` and `streamable_http_app()` create SEPARATE Starlette apps with different routes (`/sse` vs `/mcp`).
**Why it happens:** Content negotiation between SSE and Streamable HTTP is complex and not natively supported by FastMCP.
**How to avoid:** Keep SSE and Streamable HTTP as separate transports with separate endpoints. The existing `run_server()` already handles this correctly -- `transport="sse"` uses `/sse`, `transport="http"` uses `/mcp`. Content negotiation on a shared endpoint would require custom ASGI middleware, which is unnecessary complexity.
**Warning signs:** Attempting to merge SSE and Streamable HTTP on a single route path.

### Pitfall 6: Pre-existing Test Failures
**What goes wrong:** Two tests in `test_server.py` fail: `TestIndexCodebase::test_returns_success_dict` and `TestIndexCodebase::test_derives_index_name`. Both fail because `register_index_path()` is not mocked and tries to connect to PostgreSQL.
**Why it happens:** These tests mock `run_index` but don't mock `register_index_path`, which was added later. When PostgreSQL is unavailable, `register_index_path` raises an exception that gets caught by the generic `except Exception`, returning `{"success": False}`.
**How to avoid:** These are pre-existing failures unrelated to Phase 45. Fix them by adding `patch("cocosearch.mcp.server.register_index_path")` to the affected tests. Include this fix in the phase plan.

## Code Examples

Verified patterns from installed SDK source code:

### Complete _detect_project() Helper
```python
from pathlib import Path
from urllib.parse import urlparse, unquote
from mcp.server.fastmcp import Context
from mcp.types import ClientCapabilities, RootsCapability
from mcp.shared.exceptions import McpError

def file_uri_to_path(uri: str) -> Path | None:
    """Convert file:// URI to filesystem Path (Unix only)."""
    if not uri.startswith("file://"):
        return None
    parsed = urlparse(uri)
    decoded_path = unquote(parsed.path)
    if not decoded_path:
        return None
    return Path(decoded_path)

async def _detect_project(ctx: Context) -> tuple[Path | None, str]:
    """Detect project path using priority chain: roots > query_param > env > cwd.

    Returns:
        (path, source) where source is "roots", "query_param", "env", or "cwd"
    """
    # 1. Try MCP Roots capability
    try:
        session = ctx.session
        if session.check_client_capability(
            ClientCapabilities(roots=RootsCapability())
        ):
            result = await session.list_roots()
            for root in result.roots:
                path = file_uri_to_path(str(root.uri))
                if path and path.exists():
                    return path, "roots"
    except (McpError, Exception):
        pass  # Fall through to next source

    # 2. Try HTTP query parameter
    try:
        request = ctx.request_context.request
        if request is not None:
            project_path = request.query_params.get("project_path")
            if project_path:
                path = Path(project_path)
                if path.is_absolute() and path.exists():
                    return path, "query_param"
    except (AttributeError, Exception):
        pass

    # 3. Try environment variable
    import os
    env_path = os.environ.get("COCOSEARCH_PROJECT_PATH") or os.environ.get("COCOSEARCH_PROJECT")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path, "env"

    # 4. Try cwd
    cwd = Path.cwd()
    return cwd, "cwd"
```

### Converting Sync Tool to Async with Context
```python
# BEFORE (current sync tool):
@mcp.tool()
def search_code(query: str, index_name: str | None = None) -> list[dict]:
    if index_name is None:
        root_path, detection_method = find_project_root()
    ...

# AFTER (async tool with Context):
@mcp.tool()
async def search_code(
    query: Annotated[str, Field(description="...")],
    ctx: Context,
    index_name: Annotated[str | None, Field(description="...")] = None,
) -> list[dict]:
    if index_name is None:
        root_path, source = await _detect_project(ctx)
    ...
```

### Registering Roots Change Notification Handler
```python
from mcp.types import RootsListChangedNotification

async def _handle_roots_changed(notification: RootsListChangedNotification) -> None:
    """Handle roots/list_changed notification from client."""
    logger.info("Roots list changed, will re-detect on next tool call")
    # No caching needed if _detect_project() is called fresh each time

# Register during server setup (after mcp = FastMCP("cocosearch")):
mcp._mcp_server.notification_handlers[RootsListChangedNotification] = _handle_roots_changed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `COCOSEARCH_PROJECT_PATH` env var | Roots capability (primary) | Phase 45 | Protocol-correct detection for roots-capable clients |
| `find_project_root()` from cwd | `_detect_project()` priority chain | Phase 45 | Unified detection across all transports |
| Sync tool functions | Async tool functions | Phase 45 | Required for Context/session access |

**Deprecated/outdated:**
- `fastmcp` as separate package: merged into `mcp` package as `mcp.server.fastmcp` since mcp v1.x. There is no separate `fastmcp` pip package to install.
- MCP SDK v2: explicitly out of scope (pre-alpha). Stay on v1.26.x.

## Open Questions

Things that couldn't be fully resolved:

1. **Shared /mcp endpoint for SSE + Streamable HTTP**
   - What we know: FastMCP creates separate Starlette apps for SSE and Streamable HTTP with different route paths (`/sse` vs `/mcp`). The CONTEXT.md says "shared /mcp endpoint handles both."
   - What's unclear: Whether content negotiation is worth implementing or if separate endpoints suffice.
   - Recommendation: Keep separate transport modes as-is. The existing `run_server(transport="sse"|"http")` pattern works. Do NOT attempt to merge on a single endpoint -- it adds complexity for minimal user benefit. Update CONTEXT.md decision if needed.

2. **Roots notification with cached detection**
   - What we know: The low-level server accepts notification handlers via `notification_handlers` dict. `RootsListChangedNotification` is defined in types.
   - What's unclear: Whether project detection should be cached (and invalidated on roots change) or re-detected on every tool call.
   - Recommendation: Re-detect on every tool call (simpler, no cache to invalidate). The `list_roots()` call is lightweight. Register the notification handler for logging only.

3. **HTTP 400 for invalid project_path**
   - What we know: The CONTEXT.md says "Invalid path: return 400 Bad Request." However, query params are processed inside tool handlers (after the HTTP layer has accepted the request).
   - What's unclear: Whether to return HTTP 400 (requires middleware) or return an error in the tool response (within MCP protocol).
   - Recommendation: Return error in the tool response (like the existing "No project detected" pattern), not HTTP 400. Middleware would be complex and inconsistent with MCP protocol semantics.

## Sources

### Primary (HIGH confidence)
- **Installed MCP SDK v1.26.0 source code** - Direct inspection of:
  - `mcp/server/fastmcp/server.py` - FastMCP class, Context class, tool decorator, `run()` method
  - `mcp/server/session.py` - `ServerSession.list_roots()`, `check_client_capability()`
  - `mcp/shared/context.py` - `RequestContext` dataclass (request field)
  - `mcp/types.py` - `Root`, `ListRootsResult`, `ClientCapabilities`, `RootsCapability`, `FileUrl`, `RootsListChangedNotification`
  - `mcp/server/lowlevel/server.py` - `notification_handlers`, `request_ctx` ContextVar, `get_capabilities()`
  - `mcp/server/sse.py` - SSE transport, `ServerMessageMetadata(request_context=request)` at line 244
  - `mcp/server/streamable_http.py` - Streamable HTTP transport, `_create_session_message()` at line 236
  - `mcp/server/streamable_http_manager.py` - Session manager, `handle_request()` dispatch
  - `mcp/server/fastmcp/utilities/context_injection.py` - `find_context_parameter()` for Context auto-injection

### Secondary (MEDIUM confidence)
- **Codebase inspection** (`src/cocosearch/mcp/server.py`) - Current tool implementations, run_server(), transport handling
- **Test suite inspection** (`tests/unit/mcp/test_server.py`) - Pre-existing failures identified and root-caused

### Tertiary (LOW confidence)
- None -- all findings verified against installed source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified against installed mcp v1.26.0 source
- Architecture: HIGH - All patterns verified by inspecting actual SDK implementations
- Pitfalls: HIGH - Identified through source code analysis and running tests
- Roots API: HIGH - Confirmed `ServerSession.list_roots()` signature and `Root` type
- Query param access: HIGH - Confirmed `request_context.request` chain through SSE and Streamable HTTP transports
- file:// URI parsing: HIGH - Tested with Python interpreter, verified `urlparse`+`unquote` vs `FileUrl.path`
- Notification handlers: HIGH - Confirmed `notification_handlers` dict on low-level server
- Shared endpoint: MEDIUM - Recommendation to NOT merge; may conflict with CONTEXT.md decision

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable -- mcp v1.26.x, no major version changes expected)
