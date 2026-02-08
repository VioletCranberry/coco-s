# Phase 46: Parse Failure Tracking - Context

**Gathered:** 2026-02-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Track and surface tree-sitter parse failures per language in stats output. Users can see how many files failed parsing, which files, and why — across CLI stats, MCP index_stats tool, and HTTP /api/stats endpoint. Creating new parsing strategies or fixing tree-sitter grammars is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Parse status categories
- Four statuses: `ok`, `partial`, `error`, `unsupported`
- `ok` — clean parse, no ERROR nodes in tree
- `partial` — tree-sitter produced a tree but with ERROR nodes; chunks still extracted and indexed
- `error` — total failure anywhere in the parse-through-chunking pipeline (no usable output)
- `unsupported` — language not supported by tree-sitter at all
- Status covers the full extraction pipeline (tree-sitter parse + chunking), not just tree-sitter alone
- Partial parses: index whatever chunks were successfully extracted, mark status as `partial`

### Stats display format
- CLI: inline per-language columns — e.g., `Python: 142 files, 138 ok, 3 partial, 1 error, 0 unsupported`
- Always show all status columns (including zeros) for consistency
- Summary line with overall parse health percentage: `Parse health: 95.2% clean (142/149 files)`
- MCP/HTTP: nested per-language object — `{"python": {"files": 142, "ok": 138, "partial": 3, "error": 1, "unsupported": 0}}`
- Include top-level `parse_health_pct` in API responses

### Failure detail level
- Store individual file paths that failed (not just aggregate counts)
- Store error messages/details alongside file paths — users can understand WHY a file failed
- Failed file details surfaceable through all stats endpoints (CLI, MCP, HTTP)
- CLI: opt-in via `--show-failures` flag (keeps default output clean)
- MCP/HTTP: include failure details in response (or as optional parameter)

### Storage approach
- Separate `parse_results` table (not a column on chunks)
- Per-file granularity: one row per file with path, language, status, error_message
- Scoped to project/index — multi-repo setups keep parse results independent
- Rebuild on each index run — drop and recreate, always reflects current state

### Claude's Discretion
- Exact table schema and column types
- Migration strategy for new table
- How to detect ERROR nodes in tree-sitter output
- Chunking failure detection approach
- MCP/HTTP parameter design for optional failure detail inclusion

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-parse-failure-tracking*
*Context gathered: 2026-02-08*
