# Phase 3: Search - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Natural language search over indexed code. Users query with text, receive semantically relevant code chunks with file paths, line numbers, and relevance scores. Index management (create, delete, list) is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Output format
- Default output: JSON (structured for piping to other tools)
- Alternative: `--pretty` flag for rich formatted human-readable output
- JSON includes full context: file_path, start_line, end_line, score, chunk_content, surrounding_lines

### Result presentation
- Context lines: configurable via `--context=N` flag, default 5 lines
- Grouping: results from same file grouped together, file header shown once per group
- Relevance scores: displayed as decimal (0.87 similarity)

### Query behavior
- Default result count: 10 results
- Language filtering: both `--lang=python` flag and inline `lang:python` syntax
- No results: return empty JSON array `[]` with exit code 0 (silent)
- Minimum score: configurable via `--min-score` flag with sensible default

### CLI experience
- Command structure: query as default action (`cocosearch 'my query'`)
- Index selection: auto-detect from cwd, override with `--index=name` flag
- Interactive mode: `--interactive` flag for REPL mode
- No pager: direct output, user pipes to less if needed

### Claude's Discretion
- Pretty output style (compact vs spacious)
- Default minimum score threshold value
- REPL prompt and behavior details

</decisions>

<specifics>
## Specific Ideas

- Command feels like `cocosearch 'auth handler'` — query is the default action, not a subcommand
- JSON-first design for MCP/tool integration, with `--pretty` for humans
- Grep-like filtering behavior with `lang:` inline syntax

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-search*
*Context gathered: 2026-01-25*
