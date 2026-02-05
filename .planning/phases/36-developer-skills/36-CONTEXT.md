# Phase 36: Developer Skills - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Create skill documentation files for Claude Code and OpenCode that help developers set up CocoSearch and know when to use it vs alternatives. Skills are guidance documents, not code.

</domain>

<decisions>
## Implementation Decisions

### Skill Structure
- Compact format (~100 lines per skill)
- Direct/terse tone — bullet points, minimal prose
- No troubleshooting sections — keep focused, troubleshooting lives in README
- Same structure for both Claude Code and OpenCode skills — consistency, only config differs

### Routing Guidance
- Decision tree format — explicit "if X, use CocoSearch; if Y, use grep" branching
- Compare against grep/ripgrep/find AND IDE tools (go-to-definition, find-references)
- Include query examples inline with each routing scenario
- Explicitly state anti-patterns — "Don't use CocoSearch for: exact string matches, single-file edits..."

### Installation Flow
- Use UV (not pip) for installation: `uv pip install` or `uvx` flow
- Include explicit verification step: "Run `cocosearch stats` to verify"
- Show both project-level (.mcp.json) and global (~/.claude/) config options with tradeoffs
- UV only — no Docker mention in skills (advanced setup)

### Workflow Examples
- 5+ examples per skill for comprehensive coverage
- Show expected output format (query + truncated output)
- Prioritize hybrid + symbol filter examples — the power combo
- Include context expansion (--context flag) examples

### Claude's Discretion
- Exact example scenarios to include
- Output truncation style
- Section ordering within compact format

</decisions>

<specifics>
## Specific Ideas

- Decision tree should help AI assistants route to CocoSearch vs grep/ripgrep quickly
- Examples should demonstrate what CocoSearch does best (semantic understanding + symbol awareness)
- Verification with `cocosearch stats` confirms MCP connection working

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 36-developer-skills*
*Context gathered: 2026-02-05*
