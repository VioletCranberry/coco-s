# Phase 7: Documentation - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

User documentation enabling new users to install, configure, and use CocoSearch. Includes installation guide (Ollama, PostgreSQL, cocosearch), MCP configuration guides (Claude Code, Claude Desktop, OpenCode), CLI reference, and README quick start. All documentation lives in a single README.md file.

</domain>

<decisions>
## Implementation Decisions

### Doc Structure & Format
- Single README.md file — everything in one place, GitHub-native
- Context first structure — what it is, why use it, then installation
- Include diagrams and screenshots — architecture diagram, workflow visuals, CLI output
- Beginner friendly tone — explain prerequisites, link to external guides where helpful

### Installation Guide Depth
- Step-by-step commands for all prerequisites (brew/docker/pip)
- Cover all platforms — macOS, Linux, Windows (with caveats where needed)
- No troubleshooting section — keep docs clean, users can file issues
- Database setup: show both Docker one-liner AND native PostgreSQL + pgvector options

### MCP Configuration Guides
- Client-specific sections — separate section for each client (Claude Code, Claude Desktop, OpenCode)
- JSON config snippets only — no screenshots of settings UI
- Detailed verification steps — step-by-step to confirm server running, tools available

### CLI Reference Style
- Organized by workflow — group by task: "Indexing", "Searching", "Managing"
- Synopsis + one example per command — concise, not exhaustive
- Show expected output — include what user will see after running
- Environment variables inline — mention where relevant, no separate section

### Claude's Discretion
- Exact diagram style and tooling
- Specific wording and phrasing
- Heading hierarchy within sections
- Order of content within sections

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

*Phase: 07-documentation*
*Context gathered: 2026-01-25*
