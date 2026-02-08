# Project Research Summary

**Project:** CocoSearch v1.10
**Domain:** MCP protocol compliance, Docker simplification, developer experience, pipeline observability
**Researched:** 2026-02-08
**Confidence:** HIGH

## Executive Summary

CocoSearch v1.10 is a refinement milestone that requires no new dependencies. The five changes -- MCP Roots capability, HTTP query param project context, parse failure tracking, Docker image simplification, and default DATABASE_URL -- span different architectural layers with minimal overlap, which means they can be phased by risk and dependency rather than forced into a single large release. The most important finding across all research is that these changes are structurally independent: Docker touches packaging, Roots touches protocol, parse tracking touches the pipeline, and defaults touch configuration.

The recommended approach is to lead with credential standardization and sensible defaults because every other change depends on consistent, working database connectivity. The all-in-one Docker image should be stripped of CocoSearch (making it infra-only) in the same phase, since both are infrastructure concerns. MCP Roots should follow as the core protocol enhancement, with HTTP query params as a secondary mechanism. Parse failure tracking comes last because it is purely additive and carries the least risk.

The key risks are: (1) credential mismatch breaking existing users during the `cocoindex` to `cocosearch` migration -- this must be an atomic change across docker-compose.yml, dev-setup.sh, docs, and the default DATABASE_URL constant; (2) MCP Roots graceful degradation -- Claude Desktop, OpenCode, and Claude.ai do NOT support roots, so fallback to `--project-from-cwd` is mandatory, not optional; (3) the HTTP query param approach needs SDK-level validation before implementation because the MCP SDK may not pass query params through to tool handlers.

## Key Findings

### Recommended Stack

No dependency additions or version changes required. The existing `mcp[cli]>=1.26.0` already has full Roots support (types, session API, Context access). Starlette (transitive via MCP SDK) already provides query parameter access. Tree-sitter `>=0.25.0` already has `root_node.has_error` for parse failure detection. The only infrastructure change is the Docker base image: switch from `python:3.11-slim` to `debian:bookworm-slim` (saves ~80MB, signals infra-only purpose) and upgrade PostgreSQL from 16 to 17 (aligns with docker-compose.yml).

**Core technologies (all existing, no changes):**
- `mcp[cli]>=1.26.0`: MCP SDK with FastMCP -- Roots via `ctx.session.list_roots()`, Context for async tools
- `starlette` (transitive): HTTP framework -- `Request.query_params` for project context middleware
- `tree-sitter>=0.25.0`: Code parsing -- `tree.root_node.has_error` for parse failure detection
- `psycopg[binary,pool]>=3.3.2`: PostgreSQL driver -- parse failure stats queries, no changes needed
- `debian:bookworm-slim`: Docker base image -- replaces `python:3.11-slim` for infra-only image

**Critical version constraint:** Pin `mcp[cli]>=1.26.0,<2.0.0` to avoid breakage from the anticipated v2 SDK (pre-alpha, Q1 2026). Do NOT install standalone `fastmcp` PyPI package -- it conflicts with the SDK-bundled FastMCP.

### Expected Features

**Must have (table stakes):**
- **MCP Roots capability** -- Protocol-correct project detection replacing fragile `--project-from-cwd`. Any MCP server doing workspace detection should use Roots when available. Complexity: MEDIUM.
- **Parse failure tracking** -- Essential observability for a code search tool. Users need to know if tree-sitter cannot parse their files. Track via `parse_status` column in indexed data. Complexity: LOW-MEDIUM.
- **Sensible database defaults** -- `docker compose up && cocosearch index .` should work without env var configuration. Default: `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch`. Complexity: LOW.
- **Infra-only Docker documentation** -- docker-compose.yml already exists as infra-only but is not documented as a first-class path. Complexity: LOW.

**Should have (differentiator):**
- **HTTP query param project context** -- Enables multi-project HTTP deployments via `?project=/path`. Secondary to Roots. Complexity: LOW-MEDIUM.

**Defer (v2+):**
- Multi-root project support (use first root for v1.10)
- Per-language parse failure breakdown in CLI (aggregate counts sufficient for v1.10)
- OAuth/auth on HTTP transport (local-first tool, bind to localhost)
- Parse failure auto-remediation (track and report only)

### Architecture Approach

The five changes touch distinct architectural layers with only two cross-cutting overlaps: (1) MCP Roots and HTTP query params both feed into a shared `_detect_project()` helper with a priority chain of roots > query_param > env > cwd; (2) parse failure tracking feeds into stats aggregation. The key architectural pattern is a `parse_status` column added to the indexed data via schema migration (same proven pattern as v1.7 symbol columns), avoiding unreliable global counters inside the CocoIndex Rust-backed pipeline. The Docker change is purely subtractive -- removing the python-builder stage, svc-mcp service, and all MCP-related s6 dependencies.

**Major components affected:**
1. **Docker image** (`docker/Dockerfile`, `docker/rootfs/`) -- Strip CocoSearch, keep PostgreSQL+Ollama, switch to `debian:bookworm-slim`, upgrade to pg17
2. **MCP server** (`mcp/server.py`) -- Add async `_detect_project()` helper, convert tools to async, add ContextVar middleware for HTTP query params
3. **Indexer pipeline** (`indexer/symbols.py`, `indexer/flow.py`) -- Add `parse_status` return field, collect into schema, schema migration
4. **Stats** (`management/stats.py`) -- Aggregate parse_status counts per language, surface in CLI/API/dashboard
5. **Config** (`config/env_validation.py`, `search/db.py`, `indexer/flow.py`) -- Single DEFAULT_DATABASE_URL constant, update 3+ callsites, warn on default usage

### Critical Pitfalls

1. **Credential mismatch breaks existing users** -- docker-compose.yml uses `cocoindex:cocoindex`, Docker image uses `cocosearch:cocosearch`, dev-setup.sh hardcodes cocoindex. Changing to `cocosearch:cocosearch` everywhere must be a single atomic commit. Users with existing `postgres_data/` volumes must `docker compose down -v` and re-index. Document this migration explicitly.

2. **Claude Desktop does NOT support MCP Roots** -- Per the official MCP client support matrix, Claude Desktop, OpenCode, Claude.ai, Windsurf, Cline, and Zed do NOT support roots. Only Claude Code, Cursor, and VS Code Copilot do. Roots MUST be optional with graceful fallback. Wrap `list_roots()` in try/except, fall back to env/cwd.

3. **Default DATABASE_URL enables silent wrong-database connection** -- Users who deploy to a server and forget to set the env var will silently connect to localhost:5432. Mitigation: log a WARNING when using the default, show "source: default" in `config check`.

4. **HTTP query params may not reach tool handlers** -- The MCP SDK manages the HTTP transport internally. Query parameters on `/mcp` may be stripped before reaching application code. This must be validated before implementation, not assumed to work.

5. **s6-overlay orphaned service definitions crash container** -- Leaving any reference to `svc-mcp` in the rootfs (dependencies.d, contents.d, health-check) causes the Docker container to fail. Must delete ALL 6+ files referencing svc-mcp.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Credential Standardization and Defaults

**Rationale:** Foundation for everything else. Every subsequent phase depends on consistent, working database connectivity. Lowest effort, highest friction reduction. The credential mismatch between docker-compose.yml and Docker image is a latent bug that must be fixed before any other changes.
**Delivers:** Zero-config `docker compose up && cocosearch index .` workflow. Unified credentials across all deployment modes.
**Addresses:** Sensible database defaults (Feature 5), infra-only Docker docs (Feature 4 partial)
**Avoids:** Credential mismatch pitfall (Pitfall 2), silent wrong-database pitfall (Pitfall 3)
**Files:** `config/__init__.py` or `config/defaults.py` (new constant), `search/db.py`, `indexer/flow.py`, `config/env_validation.py`, `docker-compose.yml`, `dev-setup.sh`, documentation files

### Phase 2: Docker Image Simplification

**Rationale:** Purely subtractive change -- removing code is safer than adding. Independent of protocol features. Benefits from Phase 1 credential alignment. Reduces image size by ~500MB and decouples application from infrastructure.
**Delivers:** Infra-only Docker image (PostgreSQL+pgvector + Ollama). Updated health checks. Cleaned s6-overlay dependency chain.
**Addresses:** Docker infra-only image (Feature 4)
**Avoids:** Orphaned s6 service definitions (Pitfall 11), README inconsistency (Pitfall 12), breaking existing users (Pitfall 1)
**Files:** `docker/Dockerfile`, `docker/rootfs/etc/s6-overlay/s6-rc.d/` (delete svc-mcp, update init-ready, update health-check), README

### Phase 3: MCP Roots Capability

**Rationale:** Core protocol enhancement. Replaces the fragile `--project-from-cwd` workaround with the MCP-standard mechanism. Requires making tools async and adding a shared `_detect_project()` helper. Must be implemented with graceful fallback given the poor client support matrix.
**Delivers:** Protocol-correct project detection via MCP Roots. Async tool functions. Shared detection helper with fallback chain.
**Addresses:** MCP Roots capability (Feature 1)
**Avoids:** Client compatibility crash (Pitfall 4), protocol-reality gap (Pitfall 5), FastMCP API bugs (Pitfall 6)
**Files:** `mcp/server.py` (tools become async, `_detect_project()` helper, `file://` URI parsing)

### Phase 4: HTTP Query Param Project Context

**Rationale:** Secondary to Roots -- only needed for HTTP clients that lack Roots support. Depends on the `_detect_project()` helper from Phase 3. MEDIUM risk due to uncertainty about SDK query param pass-through.
**Delivers:** `?project=/path` on HTTP endpoint URL, ContextVar middleware, integration with detection chain.
**Addresses:** HTTP query param project context (Feature 2)
**Avoids:** URL injection (Pitfall 7), SDK transport stripping (Pitfall 8)
**Files:** `mcp/server.py` (middleware class, ContextVar, run_server() modification)

### Phase 5: Parse Failure Tracking

**Rationale:** Purely additive, lowest risk, independent of all other changes. Benefits from a stable foundation. Most complex in terms of cross-cutting concerns (pipeline + schema + stats + display).
**Delivers:** `parse_status` column in indexed data, per-language failure counts in stats, schema migration, CLI/API/dashboard surfacing.
**Addresses:** Parse failure tracking (Feature 3)
**Avoids:** Useless counter without context (Pitfall 9), thread-unsafe global counters (Pitfall 10)
**Files:** `indexer/symbols.py`, `indexer/flow.py`, `indexer/schema_migration.py`, `management/stats.py`, `mcp/server.py` (index_stats tool output)

### Phase Ordering Rationale

- **Phase 1 first** because credential consistency is a prerequisite for testing everything else and eliminates the most common onboarding friction
- **Phase 2 second** because Docker simplification is a deletion operation with clear scope -- low risk, independent of application features, and benefits from Phase 1 credential alignment
- **Phase 3 third** because MCP Roots is the highest-value protocol feature and creates the `_detect_project()` helper that Phase 4 reuses
- **Phase 4 fourth** because it extends Phase 3's detection chain and its viability depends on SDK behavior discovered during Phase 3
- **Phase 5 last** because it is the most complex cross-cutting change (pipeline + schema + stats) but carries the least deployment risk
- Documentation updates should happen within each phase, not deferred to the end

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (MCP Roots):** Validate `ctx.session.list_roots()` behavior across stdio and HTTP transports. Test against Claude Code (has roots) and Claude Desktop (no roots). Verify error handling for `-32601 Method not found`. Needs `/gsd:research-phase`.
- **Phase 4 (HTTP Query Params):** Must verify whether Starlette query params are accessible through the FastMCP/MCP SDK HTTP transport layer. The `contextvars` + middleware approach is standard Starlette but its interaction with FastMCP's session model is unvalidated. Needs `/gsd:research-phase`.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Defaults):** Simple `os.getenv()` with fallback. All callsites identified. Standard pattern.
- **Phase 2 (Docker):** Deletion operation with clear file list. s6-overlay structure is well-documented. Standard pattern.
- **Phase 5 (Parse Tracking):** Same schema migration pattern as v1.7 symbol columns. `tree.root_node.has_error` is documented tree-sitter API. Standard pattern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies. All capabilities verified against installed SDK source code and tree-sitter docs. |
| Features | HIGH | Feature scope is well-defined. Classification as table stakes vs differentiator is clear from protocol spec and user expectations. |
| Architecture | HIGH | Component boundaries identified from codebase analysis. Cross-cutting concerns mapped. Build order validated against dependency graph. |
| Pitfalls | HIGH | Critical pitfalls verified against MCP client support matrix (official source), codebase inspection, and existing credential mismatches. |

**Overall confidence:** HIGH

### Gaps to Address

- **FastMCP middleware integration for HTTP query params:** The exact method to add Starlette middleware to FastMCP's ASGI app needs validation during Phase 4 implementation. Two approaches exist (wrapping the app vs using settings) but neither is confirmed.
- **MCP Roots caching strategy:** Whether to call `list_roots()` per tool invocation or cache per session depends on performance characteristics that can only be measured at runtime. Start without caching.
- **Docker image tag strategy:** Whether to publish `cocosearch:v1.10-infra` alongside `cocosearch:v1.9-allinone` or just replace the `latest` tag is a release decision, not a technical one. Needs product decision.
- **CocoIndex pipeline interaction with parse_status:** The `parse_status` field is added to `extract_symbol_metadata()` return value. Whether CocoIndex's Rust pipeline handles the extra field without schema definition changes needs verification during Phase 5.

## Sources

### Primary (HIGH confidence)
- MCP SDK v1.26.0 installed source: `.venv/lib/python3.11/site-packages/mcp/` -- Root types, session.list_roots(), Context.session property
- MCP Specification (2025-11-25): https://modelcontextprotocol.io/specification/2025-11-25/client/roots
- MCP Client Support Matrix: https://modelcontextprotocol.io/clients -- roots support per client
- py-tree-sitter Node API: https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Node.html -- has_error, is_error, is_missing
- CocoSearch codebase: `mcp/server.py`, `config/env_validation.py`, `search/db.py`, `indexer/flow.py`, `indexer/symbols.py`, `docker/Dockerfile`, `docker/rootfs/`

### Secondary (MEDIUM confidence)
- FastMCP Context docs: https://gofastmcp.com/python-sdk/fastmcp-server-context -- list_roots() API
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk -- stateless HTTP roots issue #1097
- FastMCP roots issue: https://github.com/jlowin/fastmcp/issues/326 -- set_roots notification bug
- Starlette Request API: https://www.starlette.io/requests/ -- query_params

### Tertiary (LOW confidence)
- FastMCP 3.0.0b2 pre-release (Feb 2026): https://pypi.org/project/fastmcp/ -- NOT relevant to `mcp[cli]` bundled FastMCP
- Claude Code roots behavior (mentioned in search results, not officially documented for this specific behavior)
- Cursor/VS Code MCP roots support status (listed on client matrix but behavior unverified)

---
*Research completed: 2026-02-08*
*Ready for roadmap: yes*
