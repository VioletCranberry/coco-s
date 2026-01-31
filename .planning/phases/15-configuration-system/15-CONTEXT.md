# Phase 15: Configuration System - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can configure CocoSearch behavior via YAML config file (`cocosearch.yaml`). The config system handles file loading, validation, defaults, and merging. CLI flag precedence is Phase 16.

</domain>

<decisions>
## Implementation Decisions

### Config Schema Design
- Grouped sections (logical groupings, not flat keys)
- camelCase naming convention for all config keys
- Claude determines logical section grouping based on existing CLI options
- Preserve user comments when generating/updating config files

### Error Handling & Validation
- Strict: error and stop on unknown fields (reject config entirely)
- Report all validation errors at once, not just the first
- Suggest corrections for typos ("Unknown field 'indxName'. Did you mean 'indexName'?")
- Strict type checking, no coercion (error on type mismatch, don't accept "10" as 10)

### Default Values & Merging
- Mention on first run when no config file exists ("No cocosearch.yaml found, using defaults")
- List fields replace entirely (user's `languages: [python]` means only Python, no inherited defaults)
- Add `cocosearch init` command to generate starter config
- Generated config: minimal with common options uncommented, rest as comments

### Claude's Discretion
- Exact section grouping (index, search, embedding, or other logical structure)
- Which fields go in each section
- Specific default values for each setting
- Comment format in generated config

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

*Phase: 15-configuration-system*
*Context gathered: 2026-01-31*
