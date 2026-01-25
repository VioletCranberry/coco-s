---
phase: 06-test-coverage
plan: 03
subsystem: testing
tags: [management, pytest, pytest-subprocess, mocking]
dependency_graph:
  requires: [05-02, 05-03]
  provides: [management-tests, git-mocking, subprocess-mocking]
  affects: [06-04, 06-05]
tech_stack:
  added: [pytest-subprocess>=1.5.3]
  patterns: [subprocess-mocking, multi-query-mocking, commit-verification]
key_files:
  created:
    - tests/management/__init__.py
    - tests/management/test_git.py
    - tests/management/test_discovery.py
    - tests/management/test_clear.py
    - tests/management/test_stats.py
  modified:
    - pyproject.toml
    - tests/mocks/db.py
    - tests/fixtures/db.py
    - tests/test_db_mocks.py
decisions:
  - id: subprocess-mocking-via-fp
    choice: "Use pytest-subprocess fp fixture for git command mocking"
    reason: "Clean API, avoids patching subprocess module directly"
  - id: mock-connection-commit
    choice: "Add commit() method to MockConnection with tracking"
    reason: "Needed to verify transaction commits in clear tests"
  - id: fixture-3-tuple-return
    choice: "Return (pool, cursor, conn) from mock_db_pool"
    reason: "Tests need access to connection for commit verification"
metrics:
  duration: ~6 minutes
  completed: 2026-01-25
---

# Phase 6 Plan 03: Management Tests Summary

Management module tests covering git integration, index discovery, clearing, and statistics with pytest-subprocess for git command mocking.

## What Was Built

### Test Files Created

**tests/management/test_git.py (77 lines)**
- TestGetGitRoot: 3 tests for git repo detection
- TestDeriveIndexFromGit: 3 tests for index name derivation
- Uses pytest-subprocess `fp` fixture for subprocess mocking

**tests/management/test_discovery.py (72 lines)**
- TestListIndexes: 4 tests for index listing
- Verifies table name parsing from PostgreSQL
- Tests empty results and complex names with underscores

**tests/management/test_clear.py (76 lines)**
- TestClearIndex: 5 tests for index deletion
- Verifies EXISTS check, DROP TABLE execution, commit calls
- Tests error handling for nonexistent indexes

**tests/management/test_stats.py (174 lines)**
- TestFormatBytes: 4 tests for byte formatting helper
- TestGetStats: 7 tests for statistics retrieval
- Tests edge cases: zero values, large sizes, query execution

### Infrastructure Changes

**pyproject.toml**
- Added pytest-subprocess>=1.5.3 to dev dependencies

**tests/mocks/db.py**
- Added `commit()` method to MockConnection
- Added `committed` tracking flag

**tests/fixtures/db.py**
- Updated mock_db_pool to return 3-tuple (pool, cursor, conn)
- Updated patched_db_pool fixture accordingly

## Test Coverage Summary

| Module | Functions Tested | Tests | Status |
|--------|-----------------|-------|--------|
| git.py | get_git_root, derive_index_from_git | 6 | Pass |
| discovery.py | list_indexes | 4 | Pass |
| clear.py | clear_index | 5 | Pass |
| stats.py | format_bytes, get_stats | 11 | Pass |
| **Total** | **6 functions** | **26 tests** | **All Pass** |

## Requirements Fulfilled

- TEST-MGT-01: Git integration tests (6 tests)
- TEST-MGT-02: Index discovery tests (4 tests)
- TEST-MGT-03: Index clearing tests (5 tests)
- TEST-MGT-04: Statistics tests (11 tests)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added commit method to MockConnection**
- **Found during:** Task 2
- **Issue:** clear_index calls conn.commit() which MockConnection didn't support
- **Fix:** Added commit() method with tracking flag
- **Files modified:** tests/mocks/db.py

**2. [Rule 3 - Blocking] Updated fixture to return 3-tuple**
- **Found during:** Task 2
- **Issue:** Tests needed access to connection for commit verification
- **Fix:** Changed mock_db_pool to return (pool, cursor, conn)
- **Files modified:** tests/fixtures/db.py, tests/test_db_mocks.py

**3. [Rule 3 - Blocking] Fixed patch paths in existing test files**
- **Found during:** Task 2
- **Issue:** Some tests used 2-tuple unpacking after fixture change
- **Fix:** Updated all test files to use 3-tuple unpacking
- **Files modified:** tests/search/test_query.py, tests/mcp/test_server.py

## Key Patterns Established

### Subprocess Mocking
```python
def test_returns_path_in_git_repo(fp):
    fp.register(
        ["git", "rev-parse", "--show-toplevel"],
        stdout="/home/user/myproject\n"
    )
    result = get_git_root()
    assert result == Path("/home/user/myproject")
```

### Multi-Query Mocking
```python
pool, cursor, conn = mock_db_pool(results=[
    (True,),      # First query: EXISTS check
    (10, 50),     # Second query: COUNT
    (1024*1024,), # Third query: pg_table_size
])
```

### Commit Verification
```python
result = clear_index("myindex")
assert conn.committed is True
```

## Next Phase Readiness

Ready for Plan 04 (Search Tests):
- Mock infrastructure proven for query/embedding operations
- Pattern for multi-query result sequences established
- No blockers identified
