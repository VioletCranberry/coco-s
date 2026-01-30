# Phase 14: End-to-End Flows - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Full-flow integration tests validating complete index and search pipelines with real PostgreSQL+pgvector and Ollama services. Tests exercise CLI commands end-to-end, verifying files are indexed correctly and search returns accurate results with metadata.

</domain>

<decisions>
## Implementation Decisions

### Test Fixtures
- Minimal fixture set (5-10 files) — just enough to validate each language type
- Synthetic/purpose-built content with predictable search terms for reliable assertions
- Claude decides fixture location based on pytest conventions
- Happy paths only — edge cases (empty, binary, large files) covered elsewhere

### Flow Coverage
- Happy path + key errors — success cases plus connection failures, invalid files
- Test incremental indexing — verify only changed files are re-indexed
- Validate result correctness + metadata — file paths, line numbers, language, chunk content
- Test language filtering — validate --language flag restricts results correctly

### CLI Testing
- Use subprocess — run actual CLI binary via subprocess.run()
- Assert against JSON output — parse --json flag for structured assertions
- Assert exit codes — verify 0 for success, non-zero for errors
- Test error messages — verify user-facing error text is helpful

### DevOps Validation
- Test all three file types — HCL, Dockerfile, Bash (full v1.2 coverage)
- Assert metadata — validate extracted metadata fields are correct
- Test language aliases — verify tf, docker, shell aliases work in search
- Realistic complexity — multi-stage Dockerfiles, Terraform modules

### Claude's Discretion
- Fixture directory location
- Exact error scenarios to test
- Test organization and grouping

</decisions>

<specifics>
## Specific Ideas

- Subprocess invocation gives true CLI integration testing (not in-process shortcuts)
- JSON output for assertions — more reliable than pattern matching pretty output
- Realistic DevOps fixtures test actual chunking patterns users will encounter

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-end-to-end-flows*
*Context gathered: 2026-01-30*
