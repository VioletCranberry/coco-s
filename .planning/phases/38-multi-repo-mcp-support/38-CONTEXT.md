# Phase 38: Multi-Repo MCP Support - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable single MCP registration that works across all user projects. Users register CocoSearch once (user scope) and can search any project by opening it. Covers: project detection from cwd, unindexed project handling, stale index warnings, and error messaging patterns.

</domain>

<decisions>
## Implementation Decisions

### Unindexed Project Handling
- Return guidance message (not silent failure, not blocking prompt)
- Message includes exact indexing command with correct project path
- Differentiate between "never indexed" vs "index exists for different project"
- For mismatch case: explain the mismatch + provide reindex command

### Stale Index Warnings
- Detection method: Claude's discretion (git-based, file mtime, or threshold — choose most reliable)
- Warning presentation: footer note after search results (not blocking, not prominent)
- Include brief reindex hint: "Run `coco index` to refresh"
- Single warning level — no severity gradation

### Project Detection
- Primary: walk up from cwd to find .git directory (git root = project root)
- Fallback: if no .git found, use cwd as-is
- Monorepos: treat as single project (top-level git root, not sub-projects)
- Always show resolved project path in search results header ("Searching: /path/to/project")

### Error Messaging
- Tone: friendly + actionable (conversational, clear next steps)
- Include common causes beyond immediate fix
- Unexpected errors: show full traceback for debugging
- Consistent structure across all MCP tools: `[Type] Message. Fix: command. (Common causes: ...)`

### Claude's Discretion
- Staleness detection algorithm choice
- Exact wording of error messages
- Edge case handling not covered above

</decisions>

<specifics>
## Specific Ideas

- Error format example: "No index found for this project. Run: `coco index /path/to/project`. Common causes: new project, moved directory, cleared cache."
- Header example: "Searching: /Users/me/projects/my-app"
- Staleness note example: "Note: Index may be stale. Run `coco index` to refresh."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 38-multi-repo-mcp-support*
*Context gathered: 2026-02-05*
