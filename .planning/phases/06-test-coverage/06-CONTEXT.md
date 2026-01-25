# Phase 6: Test Coverage - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Full test suite covering all CocoSearch modules with mocked dependencies. Tests for indexer, search, management, CLI, and MCP server modules. Uses the mocking infrastructure established in Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Test organization
- Mirror source structure: `tests/indexer/test_config.py` for `src/cocosearch/indexer/config.py`
- Test naming: `test_<scenario>_<outcome>` (e.g., `test_valid_query_finds_matches`)
- Group tests with classes by function: `class TestSearch:` with methods for each scenario
- Fixture location: Shared fixtures in root `tests/conftest.py`, module-specific fixtures inline in test files

### Coverage scope
- Comprehensive: Happy paths, edge cases, all error branches, boundary conditions
- 80% coverage threshold enforced in CI
- All modules get equal priority — consistent depth across the codebase

### Test isolation
- Full mocking: Always mock DB and Ollama — tests never touch real services
- Mock at boundaries only: Mock DB/Ollama, but let internal modules call each other
- Filesystem: Mock pathlib/os — no real filesystem operations in tests

### Assertion style
- Exact matches: Assert full output matches expected (catches regressions)
- Error cases: `pytest.raises` with message check — verify exception type AND message content
- Logging: Verify important events with `caplog`
- CLI output: Check content, not format — verify data is present, ignore Rich formatting details

### Claude's Discretion
- Whether tests can share module-level state for performance (vs complete isolation)
- Which log messages are "important" enough to verify
- Exact structure of test helper functions

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-test-coverage*
*Context gathered: 2026-01-25*
