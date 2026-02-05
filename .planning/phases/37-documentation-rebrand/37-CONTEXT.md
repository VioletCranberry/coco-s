# Phase 37: Documentation Rebrand - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Update README to accurately reflect CocoSearch's full capabilities — hybrid search, symbol filtering, context expansion, stats dashboard. Move beyond the original "semantic code search" positioning to match v1.8 feature set.

</domain>

<decisions>
## Implementation Decisions

### Positioning & Tagline
- Lead with "Hybrid search for codebases" as core value proposition
- Local/privacy execution mentioned secondary (in description paragraph, not tagline)
- MCP and CLI framed as equal citizens: "Works as CLI or MCP server"
- Differentiation angle: Claude's discretion (likely emphasize the combination of capabilities)

### Feature Hierarchy
- Hybrid search (semantic + keyword fusion) leads the feature list
- Language support grouped by tier (full support vs basic support if coverage varies)
- Stats dashboard gets dedicated "Observability" section (not main features, not footnote)
- Caching mentioned as performance feature ("fast repeated queries")

### Audience & Tone
- Primary audience: Both CLI users and MCP/AI tool users equally
- Tone: Friendly and approachable — conversational, explains concepts, welcoming
- Technical depth: Middle ground — core usage in README, advanced topics linked to separate docs
- No comparison section — let features speak for themselves

### Structure & Sections
- After tagline: Quick start (jump straight to installation and basic usage)
- CLI Usage and MCP Integration as separate top-level sections
- Examples use real code (CocoSearch codebase or well-known repos)
- Include Contributing guide section
- No Troubleshooting/FAQ in README (keep focused)

### Claude's Discretion
- Exact tagline wording
- Differentiation angle (semantic understanding vs all-in-one vs context-aware)
- How to tier the 10 languages (what counts as "full" vs "basic" support)
- Section ordering beyond the constraints above
- Whether to include badges (build status, version, etc.)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 37-documentation-rebrand*
*Context gathered: 2026-02-05*
