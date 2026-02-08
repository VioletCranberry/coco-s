# Domain Pitfalls: CocoSearch v1.10

**Domain:** Docker simplification, MCP Roots, credential standardization, parse tracking
**Researched:** 2026-02-08
**Confidence:** HIGH (verified against codebase, MCP spec, and MCP client support matrix)

---

## Critical Pitfalls

Mistakes that cause broken user setups, protocol violations, or data loss.

---

### Pitfall 1: Docker Image Stripping Breaks Existing Users

**What goes wrong:** The current Docker image (v1.6+) is documented as "all-in-one" and bundles PostgreSQL+pgvector, Ollama+model, AND the CocoSearch MCP server. Stage 2 of the Dockerfile (`python-builder`) installs CocoSearch into `/app/.venv`, and the `svc-mcp` s6 service runs `python -m cocosearch mcp`. Users who followed README "Option #1" or the Docker Quick Start have `docker run` commands that depend on the MCP server being inside the image. Stripping the application code means those existing `docker run` commands will fail with a missing `cocosearch` module error -- a silent, confusing break at container start time.

**Why it happens:** The Dockerfile currently has three stages: model-downloader, python-builder, and final runtime. The python-builder stage copies the full application. Removing it also requires removing the `svc-mcp` s6 service definition (and its dependencies and readiness checks), the Python virtual environment, the `PYTHONPATH` env var, and the health check that tests MCP availability. It is easy to forget one of these coupled components.

**Consequences:**
- Users with existing `docker run` commands get opaque s6 service failure messages
- The `init-ready` service depends on `svc-mcp`, so the container may never report healthy
- Docker Compose configurations referencing the all-in-one image stop working
- Claude Desktop HTTP/SSE MCP configs pointing at the container break

**Warning signs:**
- Health check failures after image rebuild
- s6-overlay error logs mentioning missing service dependencies
- Container starts but port 3000 never responds

**Prevention:**
1. Remove the entire `svc-mcp` s6 service directory AND its entries in `init-ready/dependencies.d/` and `user/contents.d/`
2. Remove the `init-ready` oneshot entirely (it only exists to signal that all services including MCP are ready) or redefine it to depend only on `svc-postgresql` and `svc-ollama`
3. Remove Stage 2 (`python-builder`) and all `COPY --from=python-builder` lines
4. Remove `PYTHONPATH`, the `/app/.venv/bin` from `PATH`, and port 3000 from `EXPOSE`
5. Update the health check to only test PostgreSQL and Ollama (drop MCP check)
6. Update ALL documentation referencing the all-in-one image: README Option #1, Docker Quick Start docs, MCP configuration docs that show HTTP transport to the container
7. Consider adding a deprecation notice BEFORE the stripping release, or include a version tag (`cocosearch:v1.9-allinone` vs `cocosearch:v1.10-infra`)

**Detection:** Run the new image and verify: (a) no s6 service errors in logs, (b) health check passes with only PostgreSQL and Ollama, (c) port 3000 is NOT exposed, (d) `python -m cocosearch` fails gracefully (module not found, not a cryptic error).

**Which phase should address it:** Docker simplification phase. Must be coordinated with documentation update phase.

---

### Pitfall 2: Credential Mismatch During docker-compose.yml Migration

**What goes wrong:** The current `docker-compose.yml` uses `cocoindex:cocoindex` credentials (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB all set to `cocoindex`). The Docker image uses `cocosearch:cocosearch`. The `dev-setup.sh` script hardcodes `COCOSEARCH_DATABASE_URL="postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"`. The MCP configuration docs show the same cocoindex credentials. Changing docker-compose.yml to `cocosearch:cocosearch` breaks EVERY existing user who has:
- A running PostgreSQL container with `cocoindex` database and user
- Shell rc files with `export COCOSEARCH_DATABASE_URL="postgresql://cocoindex:cocoindex@..."`
- MCP client JSON configs with the old credentials
- Indexed data in the `cocoindex` database

**Why it happens:** The project originally used CocoIndex defaults. Three separate credential surfaces evolved independently: docker-compose.yml, Docker all-in-one image, and documentation examples. Standardizing requires changing all three simultaneously, plus user migration.

**Consequences:**
- `dev-setup.sh` fails because PostgreSQL rejects authentication with old credentials
- Existing PostgreSQL data volumes have a `cocoindex` database and user -- the new `cocosearch` user does not exist
- Users who set the env var in `.bashrc`/`.zshrc` will silently connect to nothing
- MCP server fails to start due to authentication error, Claude Code shows "disconnected"

**Warning signs:**
- `psycopg.OperationalError: FATAL: password authentication failed for user "cocosearch"`
- `cocosearch config check` shows DATABASE_URL as set but connection fails
- Docker containers start but cocosearch commands hang or error

**Prevention:**
1. Document the migration explicitly: "If you have existing data, either (a) recreate with new creds, or (b) update your env var to keep old creds"
2. Change docker-compose.yml, dev-setup.sh, AND all documentation examples in the SAME commit
3. For users with existing `postgres_data` volume: the PostgreSQL data directory already has `cocoindex` user baked in. New credentials only apply to fresh `initdb`. Document that users must either `docker compose down -v` (lose data, re-index) or manually create the new user/database
4. Consider making the default DATABASE_URL value match the docker-compose.yml credentials -- if the default changes to `cocosearch:cocosearch`, the docker-compose.yml MUST also change to `cocosearch:cocosearch` in the same release
5. Update the README, docs/mcp-configuration.md (which has `cocoindex:cocoindex` in 4 places), and dev-setup.sh

**Detection:** After the change, run `./dev-setup.sh` from a fresh clone AND from a clone with existing `postgres_data/` directory. Both must work or provide clear error messages.

**Which phase should address it:** Credential standardization phase. Must be a single atomic change across all files.

---

### Pitfall 3: Changing DATABASE_URL Default Breaks Users Who Rely on the Required-Variable Pattern

**What goes wrong:** Currently `COCOSEARCH_DATABASE_URL` is REQUIRED -- if not set, the application exits with a clear error via `env_validation.py`. Six separate code locations check for this variable: `flow.py` (line 199), `cli.py` (line 980), `env_validation.py` (line 34), and `db.py` (line 36). Adding a default value changes the contract from "must configure" to "works by convention." Users who have infrastructure on non-default ports, hosts, or credentials will silently connect to the wrong database if they forget to set the variable in a new environment.

**Why it happens:** The intent is to reduce friction: if docker-compose.yml uses `cocosearch:cocosearch` and the default matches, new users need zero configuration. But this creates a "works on my machine" problem where the implicit default works locally but fails in any other deployment.

**Consequences:**
- User deploys to a server, forgets to set DATABASE_URL, app silently tries localhost:5432 which may be a different PostgreSQL instance
- User's CI/CD pipeline indexes into the wrong database because the default is used instead of the CI database
- Subtle data corruption: writes go to unintended database, searches return wrong results

**Warning signs:**
- `cocosearch config check` shows DATABASE_URL with "source: default" -- user may not notice this
- Search returns 0 results because the default database has no indexes
- Indexing succeeds but data appears in wrong database

**Prevention:**
1. Make the default ONLY apply when the validation check would have failed -- log a WARNING when using the default: `"Using default DATABASE_URL (postgresql://cocosearch:cocosearch@localhost:5432/cocosearch). Set COCOSEARCH_DATABASE_URL to override."`
2. Update `cocosearch config check` to show the source of each variable (default vs env vs config)
3. Keep the current `env_validation.py` check but change it from "error if missing" to "warn if using default"
4. Do NOT change the default in the Docker image's ENV (it already sets the correct value). This change only affects native/uvx usage.
5. Update ALL 4+ code locations that check for DATABASE_URL simultaneously

**Detection:** Run `cocosearch config check` without setting the env var. Verify the output clearly shows "using default" with a warning, not silent success.

**Which phase should address it:** Credential standardization phase, specifically when updating defaults.

---

## Moderate Pitfalls

Mistakes that cause delays, confusing behavior, or protocol non-compliance.

---

### Pitfall 4: MCP Roots -- Clients That Do Not Support Roots

**What goes wrong:** The MCP specification defines roots as a CLIENT capability. The server requests roots via `roots/list`. However, not all MCP clients declare roots support. Based on the official MCP client support matrix (modelcontextprotocol.io/clients, verified 2026-02-08):

| Client | Roots Support |
|--------|--------------|
| Claude Code | YES |
| Claude Desktop | NO |
| Claude.ai | NO |
| OpenCode | NO |
| Cursor | YES |
| VS Code Copilot | YES |
| Windsurf | NO |
| Cline | NO |
| Zed | NO |

Claude Desktop, OpenCode, and Claude.ai -- three of CocoSearch's documented target clients -- do NOT support roots. If the server calls `ctx.list_roots()` when the client lacks roots capability, it will get a JSON-RPC error (`-32601 Method not found`).

**Why it happens:** Roots is a relatively new capability. Many clients implemented tools support first. The server must check whether the client declared `roots` capability during initialization before attempting to use it.

**Consequences:**
- Unhandled `-32601` error crashes the tool invocation for Claude Desktop users
- Server logs fill with JSON-RPC errors
- CocoSearch appears broken on Claude Desktop even though it worked before v1.10

**Prevention:**
1. Roots MUST be a graceful enhancement, not a requirement. The server must check for roots capability before calling `list_roots()`
2. Fall back to the existing `--project-from-cwd` / `COCOSEARCH_PROJECT_PATH` mechanism when roots are unavailable
3. Priority chain: Roots (if available) > `COCOSEARCH_PROJECT_PATH` env var > `find_project_root(cwd)` > explicit `index_name` parameter
4. Wrap `ctx.list_roots()` in a try/except that catches the JSON-RPC error and falls back gracefully
5. Log which detection method was used: `"Project detected via MCP Roots"` vs `"Project detected via cwd"`
6. Test against EACH target client: Claude Code (has roots), Claude Desktop (no roots), OpenCode (no roots)

**Detection:** Start the MCP server with `--transport stdio` connected to Claude Desktop. Call `search_code` without `index_name`. Verify it falls back to cwd detection, not crashes.

**Which phase should address it:** MCP Roots implementation phase. This is the single most important design constraint.

---

### Pitfall 5: MCP Roots -- Protocol vs Reality Gap

**What goes wrong:** The MCP specification says roots are `file://` URIs and represent filesystem boundaries. However, the spec also says: "Servers SHOULD respect root boundaries during operations" -- this is a SHOULD, not a MUST. More importantly, the spec says nothing about how roots map to "projects" or "indexes." CocoSearch needs to translate a root URI like `file:///home/user/projects/myproject` into an index name like `myproject`. This mapping is CocoSearch-specific logic, not protocol-defined.

**Why it happens:** Roots are designed for filesystem access control (limiting where a server can read/write), not for project identification. CocoSearch is repurposing roots for project detection, which is a valid but non-standard use. The mapping from root URI to index name requires the same logic currently in `resolve_index_name()`: check `cocosearch.yaml` in the root path, fall back to directory name, handle collisions.

**Consequences:**
- Multiple roots: A client may send multiple roots (e.g., frontend and backend repos). CocoSearch must decide which one is "the project" or support multi-root search
- Root URI format: `file:///home/user/projects/myproject` needs to be parsed to extract the filesystem path, then resolved to an index
- Root changes: Client may send `notifications/roots/list_changed` mid-session. CocoSearch must handle this gracefully
- Platform differences: Windows uses `file:///C:/Users/...` format

**Prevention:**
1. Parse root URIs using `urllib.parse.urlparse` -- extract the path component, handle platform differences
2. For multiple roots: use the FIRST root as primary project, log a warning about multiple roots
3. Subscribe to `notifications/roots/list_changed` and invalidate any cached project detection
4. Reuse the existing `find_project_root()` and `resolve_index_name()` logic, just change the input from cwd to root path
5. Handle edge case: root path has no `cocosearch.yaml` and no `.git` directory (it is a valid root but not a recognizable project)

**Detection:** Test with a client that sends multiple roots. Test with a root that changes mid-session. Test with a root that is not a git repository.

**Which phase should address it:** MCP Roots implementation phase.

---

### Pitfall 6: MCP Roots -- FastMCP API Compatibility

**What goes wrong:** CocoSearch uses `mcp[cli]>=1.26.0` (the official MCP Python SDK which includes FastMCP). The server is created via `FastMCP("cocosearch")`. The FastMCP Context object provides `ctx.list_roots()` for server-side root access. However, there is an open issue (FastMCP GitHub issue #326) reporting that `set_roots` + `send_roots_list_changed` does not correctly update roots on the server side in some transport configurations. Additionally, the official MCP SDK v2 is anticipated for Q1 2026 -- API changes are possible.

**Why it happens:** FastMCP 1.0 was absorbed into the official MCP SDK. There may be differences between the standalone FastMCP and the SDK-bundled version. The roots API on the server side (reading roots from the client) is less battle-tested than the tool/resource APIs.

**Consequences:**
- `ctx.list_roots()` returns stale data after client updates roots
- Different behavior between stdio and HTTP transports
- SDK upgrade could break the roots implementation

**Prevention:**
1. Pin `mcp[cli]` to a specific version range in `pyproject.toml` (e.g., `>=1.26.0,<2.0.0`) to avoid surprise breakage from v2
2. Test roots with both stdio transport (Claude Code) and HTTP transport (Claude Desktop via Docker)
3. For the root change notification issue: do NOT cache roots aggressively. Call `list_roots()` on each tool invocation, or at least invalidate any root cache when `roots/list_changed` fires
4. Write integration tests that mock the roots/list response to verify fallback behavior
5. Check the `mcp` package changelog before upgrading

**Detection:** In the test suite, mock `ctx.list_roots()` returning different values between calls. Verify the server uses the latest value, not a cached one.

**Which phase should address it:** MCP Roots implementation phase. Version pinning should happen in the dependency management task.

---

### Pitfall 7: HTTP Query Parameters for Project Context -- Injection and Encoding

**What goes wrong:** Adding query parameters to the HTTP transport URL (e.g., `http://localhost:3000/mcp?project=/path/to/code`) introduces URL injection risk. A path like `/home/user/my project&admin=true` could break parameter parsing if not properly encoded. Special characters in filesystem paths (spaces, ampersands, equals signs, Unicode, parentheses) are common on macOS and Windows.

**Why it happens:** HTTP query parameters use `key=value&key=value` format. Filesystem paths can contain `&`, `=`, `?`, `#`, `%`, and space characters -- all of which have special meaning in URLs. If the server reads query params without proper decoding, or the client does not encode them, the path will be truncated or mangled.

**Consequences:**
- Path truncation: `/home/user/my project` becomes `/home/user/my` (space not encoded)
- Parameter pollution: path containing `&` creates phantom parameters
- Path traversal: path containing `../` could theoretically be used to probe the filesystem (though CocoSearch only uses the path for index name resolution, not direct file access)
- Double-encoding: if client encodes and server also encodes, `%20` becomes `%2520`

**Prevention:**
1. Server-side: use the framework's built-in query parameter parsing (Starlette's `request.query_params` already handles URL decoding)
2. Document that clients MUST URL-encode the path parameter value
3. Validate the decoded path: must be an absolute filesystem path, must not contain null bytes
4. Sanitize: strip trailing slashes, resolve `..` components, convert to `Path` object
5. Consider using a custom header (`X-CocoSearch-Project: /path/to/code`) instead of query params -- headers handle special characters more naturally and are not visible in server logs or URL bars
6. If using query params: name the parameter clearly (`project_path`, not `path` or `p`) to avoid collision with other query params

**Detection:** Test with paths containing: spaces, ampersands, equals signs, hash characters, percent signs, Unicode characters (CJK, accented), and Windows-style backslashes.

**Which phase should address it:** HTTP transport phase.

---

### Pitfall 8: HTTP Query Parameters on Streamable HTTP Transport Path

**What goes wrong:** CocoSearch's HTTP transport uses `mcp.run(transport="streamable-http")` which serves at `/mcp`. The Streamable HTTP MCP transport has its own protocol for message framing. Adding query parameters to the MCP endpoint URL may conflict with the transport's own parameter handling, or the MCP SDK may strip query parameters before they reach the application.

**Why it happens:** The MCP Streamable HTTP transport is managed by the SDK. The server does not directly handle the HTTP request -- the SDK does. Query parameters on the MCP endpoint URL may not be passed through to tool invocations.

**Consequences:**
- Query parameters silently ignored by the SDK's HTTP handler
- Client sends `http://host:3000/mcp?project=/path` but the tool handler never sees the `project` parameter
- Breaks the project detection flow for HTTP-only clients

**Prevention:**
1. Investigate how the MCP SDK handles query parameters on the streamable-http endpoint BEFORE implementing. Check if `request.query_params` is accessible in the tool handler context
2. Alternative approach: use a SEPARATE custom route (e.g., `/connect?project=/path`) that sets a server-side session variable, then redirect to `/mcp`. This separates project context from the MCP protocol endpoint
3. Another alternative: use MCP Roots capability for project context instead of query params (preferred for clients that support it), and use `COCOSEARCH_PROJECT_PATH` env var for clients that don't
4. Test the query parameter approach with both SSE (`/sse`) and Streamable HTTP (`/mcp`) transports -- they may behave differently

**Detection:** Add a query parameter to the MCP URL in a Claude Desktop config and verify the server actually receives it in the tool handler. If not, the entire approach needs redesigning.

**Which phase should address it:** HTTP transport phase. Should be researched BEFORE implementation begins.

---

## Minor Pitfalls

Mistakes that cause annoyance or confusion but are fixable.

---

### Pitfall 9: Parse Failure Counter Without Context

**What goes wrong:** Adding a parse failure counter to the indexing pipeline (counting files that fail tree-sitter parsing) without also recording WHICH files failed and WHY makes the metric nearly useless for debugging. A user sees "12 parse failures" in stats output but has no way to fix them.

**Why it happens:** It is tempting to add a simple counter increment in the exception handler of `extract_symbol_metadata()` (symbols.py line 446-448). But the counter alone does not capture the file path, language, or error message. The current code catches `Exception` broadly and logs an error, but this log message is transient -- it disappears after the indexing session.

**Consequences:**
- Users see "12 parse failures" but cannot investigate further
- Support requests: "Why are my files failing to parse?"
- The counter may alarm users when the failures are expected (e.g., binary files miscategorized, template files with invalid syntax)

**Prevention:**
1. Track per-language failure counts (not just total) -- this immediately tells the user "8 of 12 failures are in C++ files" which points to macros
2. Store the failure details (file path, language, error type) in a transient log or in the stats output, not just a count
3. Distinguish between parse failures (tree-sitter cannot parse) and extraction failures (tree-sitter parses but no symbols found) -- the latter is normal for many file types
4. Consider a `--verbose-stats` flag that shows the failed file list, rather than always showing it
5. Do NOT store parse failure data in PostgreSQL -- it is ephemeral diagnostic data, not persistent state

**Detection:** Index a codebase known to have parse-problematic files (C++ with heavy macros). Verify the stats output gives enough information to understand what failed and whether it matters.

**Which phase should address it:** Parse tracking phase.

---

### Pitfall 10: Parse Failure Tracking in CocoIndex Transform Pipeline

**What goes wrong:** The indexing pipeline uses CocoIndex transforms (`chunk["symbol_metadata"] = chunk["text"].transform(extract_symbol_metadata, ...)`) which are declarative. CocoIndex manages the execution, and exceptions in transforms may be handled by CocoIndex's own error handling, not by CocoSearch's code. Adding a counter inside `extract_symbol_metadata()` requires careful handling because the function may be called in parallel workers.

**Why it happens:** CocoIndex transforms are designed to be pure functions. Side effects (like incrementing a global counter) are not idiomatic. CocoIndex may retry failed transforms, which would double-count failures. The function signature is constrained by CocoIndex's transform API.

**Consequences:**
- Thread-safety issues: concurrent indexing corrupts the counter
- Double-counting if CocoIndex retries transforms
- Counter state is lost between indexing runs (it is in-process memory)

**Prevention:**
1. Use a thread-safe counter (e.g., `threading.Lock` or `collections.Counter` with lock) if tracking inside the transform
2. Alternative: do NOT track inside the transform. Instead, query the indexed data after indexing completes -- count chunks where `symbol_type IS NULL` per language. This is a post-hoc metric, not a real-time counter, but it is accurate and requires no pipeline changes
3. The post-hoc approach has the advantage of working for existing indexes too (retroactive stats)
4. If real-time tracking is needed, use `logging` module with a custom handler that aggregates counts, rather than a global variable

**Detection:** Index a large codebase with `--verbose` logging. Check that the failure count in stats matches the count of logged errors.

**Which phase should address it:** Parse tracking phase.

---

### Pitfall 11: Documentation and s6 Service Definition Inconsistency

**What goes wrong:** When stripping CocoSearch from the Docker image, the s6 service definitions in `docker/rootfs/` must be updated but are easy to miss because they are not Python files. The current structure has:

- `svc-mcp/run` -- starts CocoSearch MCP server
- `svc-mcp/dependencies.d/` -- depends on init-warmup, svc-ollama, svc-postgresql
- `init-ready/dependencies.d/svc-mcp` -- ready signal depends on MCP
- `user/contents.d/svc-mcp` -- registers MCP as a user service

Leaving ANY of these in place causes s6-overlay to try to start a nonexistent service.

**Prevention:**
1. Delete the entire `svc-mcp` directory tree
2. Delete `init-ready/dependencies.d/svc-mcp`
3. Delete `user/contents.d/svc-mcp`
4. Update `init-ready/up` if it references MCP
5. Update `scripts/health-check` to remove MCP port check
6. Update `scripts/ready-signal` if it references MCP
7. Run the image and check `s6-rc -a list` to verify only postgresql and ollama services are registered

**Which phase should address it:** Docker simplification phase.

---

### Pitfall 12: README Option #1 Becomes Misleading

**What goes wrong:** README currently says "Option #1: The all-in-one Docker image bundles PostgreSQL (with pgvector), Ollama (with pre-baked nomic-embed-text model), and the CocoSearch MCP server. No separate setup required." After stripping CocoSearch from the image, this description is wrong. The image only provides infrastructure. Users need to install CocoSearch separately.

**Prevention:**
1. Rewrite Option #1 to describe the infra-only model
2. Merge Options #1 and #2 -- both now require `docker compose up` + native CocoSearch
3. Show the new recommended workflow: `docker compose up -d` + `uvx cocosearch mcp`
4. Remove or redirect Docker Quick Start docs
5. Update the `MILESTONES.md` entry for v1.6 to note the all-in-one was superseded

**Which phase should address it:** Documentation update phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Docker simplification | Orphaned s6 service definitions crash container | Delete all svc-mcp references (Pitfall 11) |
| Docker simplification | Users with existing `docker run` commands break | Major version communication, migration guide |
| Credential standardization | Existing postgres_data volumes have old creds | Document `docker compose down -v` requirement |
| Credential standardization | 4+ files reference old credentials | Single atomic commit changing all files |
| Default DATABASE_URL change | Silent wrong-database connection | Log warning when using default (Pitfall 3) |
| MCP Roots implementation | Claude Desktop / OpenCode do not support roots | Graceful fallback is mandatory (Pitfall 4) |
| MCP Roots implementation | Multiple roots from client | Use first root, log warning (Pitfall 5) |
| MCP Roots implementation | FastMCP roots API has open bugs | Pin SDK version, test both transports (Pitfall 6) |
| HTTP transport query params | SDK may not pass query params to tools | Research SDK behavior before implementing (Pitfall 8) |
| Parse failure tracking | Global counter not thread-safe | Post-hoc query approach preferred (Pitfall 10) |
| Documentation | All-in-one references now incorrect | Update README, Docker docs, MCP config docs |

---

## Recommended Risk Ordering

Based on this pitfall analysis, the v1.10 phases should be ordered to minimize cascading breakage:

1. **Credential standardization first** -- docker-compose.yml, dev-setup.sh, docs, and default DATABASE_URL all in one atomic change. This is the foundation: every subsequent change depends on consistent credentials.

2. **Docker simplification second** -- strip CocoSearch from image, update s6 services, update health check. Depends on credentials being settled.

3. **MCP Roots third** -- this is the most complex feature and has the most unknowns (client support matrix, SDK bugs, protocol mapping). Research the SDK's query parameter pass-through behavior during this phase.

4. **HTTP query params fourth** -- depends on understanding gained from Roots implementation. May be simplified or eliminated if Roots + env var covers all use cases.

5. **Parse failure tracking last** -- lowest risk, independent of other changes, pure additive feature.

6. **Documentation throughout** -- each phase should update docs as it goes, not defer to the end. The credential and Docker changes especially need same-commit doc updates.

---

## Sources

**HIGH confidence (official specification, verified against codebase):**
- MCP specification 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25
- MCP roots specification: https://modelcontextprotocol.io/specification/2025-11-25/client (roots section)
- MCP client support matrix: https://modelcontextprotocol.io/clients
- FastMCP Context API (roots): https://gofastmcp.com/python-sdk/fastmcp-server-context
- CocoSearch codebase: direct file inspection of Dockerfile, docker-compose.yml, s6 services, env_validation.py, mcp/server.py, stats.py, flow.py

**MEDIUM confidence (verified with multiple sources):**
- FastMCP roots issue #326: https://github.com/jlowin/fastmcp/issues/326
- MCP roots concept: https://www.speakeasy.com/mcp/core-concepts/roots
- HTTP parameter pollution: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/04-Testing_for_HTTP_Parameter_Pollution

**LOW confidence (general patterns, not project-specific):**
- Docker deprecation practices: https://docs.docker.com/engine/deprecated/
- SemVer and breaking changes: https://github.com/semver/semver/issues/526
