# Phase 16: CLI Config Integration - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

CLI flags override config file settings with clear precedence. Users can override any config value via CLI flag, and help text shows config equivalents. Environment variables are supported as an intermediate layer.

</domain>

<decisions>
## Implementation Decisions

### Override behavior
- Complete replacement: CLI flag replaces config entirely (no merging for lists)
- No unset mechanism needed: if you want default, don't put it in config
- CLI rescues config errors: if CLI provides valid override, ignore bad config value for that field
- Precedence chain: CLI > env var > config file > default

### Help text design
- Inline notes showing config equivalents: `--indexing.chunkSize SIZE [config: indexing.chunkSize]`
- Show effective current value with full source path: `[current: my-project from ./cocosearch.yaml]`
- Show env var names in help: `[env: COCOSEARCH_INDEXING_CHUNK_SIZE]`

### Flag naming
- Match config keys exactly (camelCase): `--indexName`, `--chunkSize`
- Dot notation for nested values: `--indexing.chunkSize` mirrors config structure
- No short flags: long flags only for clarity
- Env var pattern: `COCOSEARCH_SECTION_KEY` (e.g., `COCOSEARCH_INDEXING_CHUNK_SIZE`)

### Debug/visibility
- New `coco config` subcommand group for configuration inspection
- `coco config show`: table format with KEY | VALUE | SOURCE columns
- `coco config path`: prints config file location (or "none found")
- Config file path shown only with `--verbose` flag, silent by default

### Claude's Discretion
- Exact table formatting and column widths
- How to handle env var parsing for complex types (lists, nested objects)
- Error message wording for precedence conflicts

</decisions>

<specifics>
## Specific Ideas

- Help text should feel information-dense but scannable — user can quickly see what's configurable and where current values come from
- The `coco config show` command is for debugging "why is this value what it is?" scenarios

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-cli-config-integration*
*Context gathered: 2026-01-31*
