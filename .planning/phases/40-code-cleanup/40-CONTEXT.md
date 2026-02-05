# Phase 40: Code Cleanup - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove deprecated code and migration logic safely without breaking functionality. This includes DB migrations module, deprecated functions, and v1.2 graceful degradation code. Single-user tool means no backwards compatibility needed.

</domain>

<decisions>
## Implementation Decisions

### Removal Ordering
- Group removals logically by related functionality, not by type
- Remove leaf code first (unused code that nothing depends on), then work inward
- If code has no references found, remove it — tests will catch mistakes
- Remove related tests/fixtures together with the code they test in same commit

### Verification Approach
- Run full test suite after each removal grouping commit
- Run linters (ruff/mypy) to catch unused imports, type errors from removals
- Fix test issues inline in same commit as the removal that exposed them
- Track and report LOC reduction before/after at end of phase

### Documentation Handling
- Update comments/docstrings to reflect current behavior when removing code
- Update READMEs or external docs inline during this phase (not deferred to Phase 42)
- Resolve or remove TODO/FIXME comments that reference old patterns
- Clean up dead imports as part of cleanup — ruff will catch them

### Discovery Scope
- Include clearly dead code found during cleanup, even if not explicitly listed in requirements
- Removal only — don't fix unrelated code smells (keep concerns separate)
- Light restructuring OK if removal naturally simplifies code structure
- Review and address STATE.md blockers/concerns that are resolved by these removals

### Claude's Discretion
- Exact order of removal groupings within the "leaves first" strategy
- Judgement on what counts as "clearly dead" vs "uncertain"
- Deciding when removal naturally enables restructuring vs scope creep

</decisions>

<specifics>
## Specific Ideas

- Track LOC count before and after for reporting
- STATE.md has research flags about old index prevalence and CocoIndex schema — check if still relevant after removals

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-code-cleanup*
*Context gathered: 2026-02-05*
