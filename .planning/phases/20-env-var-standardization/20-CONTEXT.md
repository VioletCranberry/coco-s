# Phase 20: Env Var Standardization - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate all CocoSearch environment variables to consistent COCOSEARCH_* naming prefix. Update code, .env.example, docker-compose.yml, and documentation. Add config validation command.

</domain>

<decisions>
## Implementation Decisions

### Migration strategy
- Break immediately — old env var names stop working, no deprecation period
- Document changes in CHANGELOG entry only (not README)
- CHANGELOG includes full mapping table of all old → new variable names
- No migration script — users update manually based on documentation

### Default values
- COCOSEARCH_DATABASE_URL defaults to postgresql://localhost:5432/cocosearch
- COCOSEARCH_OLLAMA_URL defaults to http://localhost:11434
- .env.example contains working defaults — copy and run for local dev
- All available env vars appear in .env.example (optional ones commented out with defaults)

### Error messaging
- Missing required vars show name + hint: "Missing COCOSEARCH_DATABASE_URL. See .env.example for format."
- Fail fast at startup — validate all required vars before any work
- Show all missing vars together, not fail on first
- Add `cocosearch config check` command to validate env vars without running app

### Claude's Discretion
- Exact wording of error messages
- Organization of .env.example sections
- Whether to group related vars with comments

</decisions>

<specifics>
## Specific Ideas

- Config check command should be lightweight, no database connection needed
- .env.example should work immediately after copy for local development

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-env-var-standardization*
*Context gathered: 2026-02-01*
