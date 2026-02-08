# Phase 47: Documentation Update - Context

**Gathered:** 2026-02-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Update all documentation to accurately reflect the infra-only Docker model, new defaults, and protocol enhancements from phases 43-46. No new features — docs describe current state only.

</domain>

<decisions>
## Implementation Decisions

### Doc structure & navigation
- Rely on GitHub's auto-generated sidebar ToC — no manual table of contents at the top of each doc
- Use clear, descriptive section headers so the sidebar navigation works well
- Cross-reference other docs with inline links where naturally relevant (no "See Also" sections)
- README includes a docs section linking to each doc — no separate docs/INDEX.md
- Keep docs/ folder flat — no subfolders

### Content depth & tone
- Primary audience: developers who want to install and use CocoSearch — pragmatic, task-oriented
- Tone: friendly and conversational (like Vercel or Supabase docs)
- Describe current state only — no migration notes, no "changed in v1.10" callouts
- Include brief rationale where it genuinely aids understanding (e.g., "Docker provides infra only — CocoSearch runs natively for faster iteration")

### Quick-start flow
- 3-step minimal quick-start: `docker compose up` → index → use via MCP
- Docker is the primary setup path; mention manual PostgreSQL+Ollama setup as an alternative
- Lead with MCP registration (Claude Code/Desktop) as the main use case, CLI as secondary
- Assume Docker Desktop and Python with uv/uvx are already installed (no install instructions for these)

### Example & snippet style
- All code examples should be copy-paste ready — full commands that work as-is
- MCP config examples focus on Claude Code; mention Claude Desktop as alternative
- Show commands only — no expected output blocks (keep it lean)
- Always use `uvx cocosearch` in examples — that's the recommended invocation

### Claude's Discretion
- Exact ordering of sections within each doc
- How much detail to include in the manual (non-Docker) setup alternative
- Whether to consolidate or keep separate any existing docs that overlap

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

*Phase: 47-documentation-update*
*Context gathered: 2026-02-08*
