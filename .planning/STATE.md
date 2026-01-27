# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-27)

**Core value:** Semantic code search that runs entirely locally -- no data leaves your machine.
**Current focus:** v1.2 DevOps Language Support -- Phase 4 in progress (plan 1 of 2 complete)

## Current Position

Phase: 4 of 4 (Search and Output Integration)
Plan: 1 of 2 complete (04-01-PLAN.md)
Status: In progress
Last activity: 2026-01-27 -- Completed 04-01-PLAN.md (search query layer)

Progress: [################----] 83% (v1.2: 3/4 phases complete, 5/8 plans)

## Milestones Shipped

| Milestone | Phases | Plans | Shipped |
|-----------|--------|-------|---------|
| v1.0 MVP | 1-4 | 12 | 2026-01-25 |
| v1.1 Docs & Tests | 5-7 | 11 | 2026-01-26 |

**Total shipped:** 7 phases, 23 plans

## Active Milestone: v1.2 DevOps Language Support

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 1 | Custom Language Definitions and File Routing | 6 | ✓ Verified |
| 2 | Metadata Extraction | 7 | ✓ Verified |
| 3 | Flow Integration and Schema | 4 | ✓ Verified |
| 4 | Search and Output Integration | 9 | In Progress (1/2 plans) |

**Research flags:**
- Phase 1: RESOLVED & VERIFIED -- Bash confirmed NOT built-in, standard Rust regex, all 6 requirements complete
- Phase 2: RESOLVED & VERIFIED -- metadata.py created, 53 tests passing, all 7 requirements verified
- Phase 3: RESOLVED -- metadata wired into flow, schema extends via CocoIndex inference, all 4 requirements complete

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.2 requirements | 26 |
| v1.2 phases | 4 |
| Research confidence | HIGH |
| New dependencies | 0 |
| New files | 3 (languages.py, metadata.py, test_metadata.py) |
| Modified files | 6 (config.py, flow.py, query.py, cli.py, formatter.py, server.py) |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Key decisions for v1.2:

- Zero new dependencies (CocoIndex custom_languages + Python stdlib re)
- Single flow architecture (not separate DevOps flow)
- Regex-only approach (no external parsers)
- Empty strings over NULLs for metadata
- Metadata extraction inside the flow (not post-processing)
- Additive schema only (no primary key changes)
- Standard Rust regex only for separators (CocoIndex uses regex v1.12.2, NOT fancy-regex)
- HCL: 12 block keywords in Level 1 separator; aliases tf, tfvars
- Dockerfile: FROM at higher priority than other instructions; no aliases (routing via extract_language)
- Bash: function keyword at Level 1; aliases sh, zsh, shell; bash NOT in CocoIndex built-in list
- Bare filename patterns for Dockerfile/Containerfile (LOW confidence, needs integration validation)
- extract_language uses basename.startswith("Dockerfile") for variants, exact match for Containerfile
- Flow field kept as "extension" (not renamed to "language") to minimize changes
- chunk_size default kept at 1000 (user can configure for DevOps via .cocosearch.yaml)
- Match block keywords at chunk start only (after comment stripping)
- Language identifier passed as parameter to extract_devops_metadata (not auto-detected)
- Non-FROM Dockerfile instructions get empty hierarchy in v1.2 (no inter-chunk state)
- Top-level Bash code gets empty block_type/hierarchy (consistent with non-DevOps convention)
- Metadata transform runs unconditionally on all chunks (non-DevOps get empty strings)
- Bracket notation for struct sub-field access in collect() kwargs
- LANGUAGE_ALIASES resolves terraform->hcl, shell->bash, sh->bash before validation
- ALL_LANGUAGES = LANGUAGE_EXTENSIONS keys + DEVOPS_LANGUAGES keys; alias keys excluded
- Module-level _has_metadata_columns flag for one-time graceful degradation
- DevOps languages filter via language_id column; extension-based via filename LIKE

### Pending Todos

- Execute Phase 4 Plan 2 (Output Integration: formatters + MCP)

### Blockers/Concerns

- Bare Dockerfile filename pattern support in CocoIndex include_patterns needs validation (LOW confidence)

## Session Continuity

Last session: 2026-01-27T18:40:31Z
Stopped at: Completed 04-01-PLAN.md, ready for 04-02-PLAN.md
Resume file: .planning/phases/04-search-and-output-integration/04-02-PLAN.md

---
*Updated: 2026-01-27 after completing 04-01-PLAN.md*
