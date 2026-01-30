# Phase 14: End-to-End Flows - Research

**Researched:** 2026-01-30
**Domain:** E2E Integration Testing - CLI + Real Services
**Confidence:** HIGH

## Summary

End-to-end integration testing for CLI applications with real infrastructure (PostgreSQL+pgvector and Ollama) requires careful orchestration of subprocess execution, environment configuration, and fixture management. The standard approach uses `subprocess.run()` with actual CLI entry points, parses JSON output for assertions, and validates complete workflows from indexing through search.

**Key findings:**
- **subprocess.run()** is the standard for true CLI integration testing (not in-process calls)
- **Environment variables** from testcontainers must be propagated to subprocess calls
- **JSON output mode** is essential for reliable assertions (not parsing pretty-printed text)
- **Minimal synthetic fixtures** provide predictable results while covering all language types
- **Incremental indexing** validation requires sequential operations with file modifications

The research shows this is a well-trodden path with established patterns in pytest, testcontainers, and CLI testing. The phase builds on existing Phase 12 (PostgreSQL) and Phase 13 (Ollama) container infrastructure.

**Primary recommendation:** Use subprocess.run() with sys.executable to invoke the actual `cocosearch` CLI, propagate COCOINDEX_DATABASE_URL and OLLAMA_HOST from container fixtures, assert against parsed JSON output with jmespath for deep structure validation.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess | stdlib | CLI process execution | Built-in Python standard for running external commands |
| pytest | 9.0+ | Test framework | Already used (Phase 11), industry standard for Python testing |
| testcontainers[postgres,ollama] | 4.14+ | Container management | Already used (Phases 12-13), handles Docker lifecycle |
| json | stdlib | JSON parsing | Built-in, sufficient for CLI output validation |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path manipulation | Creating fixture directory structures |
| tempfile | stdlib | Temporary test data | Creating disposable test codebases |
| jmespath | Optional | JSON querying | Deep JSON structure assertions (cleaner than nested dict access) |
| shutil | stdlib | File operations | Copying fixtures, modifying files for incremental tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess.run() | In-process CLI calls | In-process is faster but doesn't test actual entry point, argument parsing, or sys.exit() |
| JSON parsing | Regex on pretty output | Pretty output format can change, JSON is stable contract |
| Minimal fixtures | Large real codebases | Real codebases are slow, unpredictable; synthetic fixtures have known content |
| pytest.tmp_path | Permanent fixture directory | tmp_path is cleaner but harder to debug failed tests |

**Installation:**
```bash
# Already in pyproject.toml from previous phases
pytest>=9.0.2
testcontainers[postgres,ollama]>=4.14.0
```

## Architecture Patterns

### Recommended Test Structure
```
tests/
├── integration/
│   ├── conftest.py                    # Container fixtures from Phase 12-13
│   ├── test_e2e_indexing.py          # Full index flow tests
│   ├── test_e2e_search.py            # Full search flow tests
│   ├── test_e2e_cli_commands.py      # CLI command integration
│   └── test_e2e_devops_validation.py # DevOps file type validation
├── fixtures/
│   ├── e2e_fixtures/                  # Minimal test codebase
│   │   ├── python_sample.py
│   │   ├── terraform_sample.tf
│   │   ├── Dockerfile
│   │   ├── shell_sample.sh
│   │   └── ...                        # 5-10 files total
```

### Pattern 1: Subprocess CLI Invocation

**What:** Run actual CLI binary via subprocess with environment propagation

**When to use:** All E2E tests that exercise CLI commands

**Example:**
```python
# Source: pytest best practices + testcontainers pattern
import subprocess
import sys
import os
import json

def test_index_command_e2e(test_db_url, warmed_ollama, tmp_test_codebase):
    """Test full indexing flow through real CLI."""
    # Propagate container environment to subprocess
    env = os.environ.copy()
    env["COCOINDEX_DATABASE_URL"] = test_db_url
    env["OLLAMA_HOST"] = warmed_ollama

    # Run actual CLI command
    result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "index", str(tmp_test_codebase), "--name", "test_e2e"],
        capture_output=True,
        text=True,
        env=env,
    )

    # Assert exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Parse and validate JSON output if using --json flag
    # (or validate rich output for human-readable mode)
```

### Pattern 2: JSON Output Assertions

**What:** Parse CLI JSON output and assert on structure/values

**When to use:** All CLI commands that support JSON output mode

**Example:**
```python
# Source: pytest JSON assertion patterns
import json

def test_search_returns_correct_structure(test_db_url, warmed_ollama):
    """Verify search JSON output has expected structure."""
    env = os.environ.copy()
    env["COCOINDEX_DATABASE_URL"] = test_db_url
    env["OLLAMA_HOST"] = warmed_ollama

    result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "search", "authentication", "--index", "test_e2e"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0

    # Parse JSON output
    output = json.loads(result.stdout)

    # Assert structure
    assert isinstance(output, list), "Search should return list of results"
    if output:  # If any results
        result_item = output[0]
        assert "filename" in result_item
        assert "start_line" in result_item
        assert "end_line" in result_item
        assert "score" in result_item
        assert "chunk" in result_item

        # Validate types
        assert isinstance(result_item["filename"], str)
        assert isinstance(result_item["start_line"], int)
        assert result_item["start_line"] > 0
```

### Pattern 3: Incremental Indexing Validation

**What:** Test that only changed files are re-indexed

**When to use:** Validating incremental indexing behavior

**Example:**
```python
# Source: Integration testing best practices
import shutil
from pathlib import Path

def test_incremental_indexing(test_db_url, warmed_ollama, tmp_path):
    """Verify only changed files are re-indexed."""
    # Setup: Create initial codebase
    codebase = tmp_path / "test_codebase"
    codebase.mkdir()
    (codebase / "file1.py").write_text("def foo(): pass")
    (codebase / "file2.py").write_text("def bar(): pass")

    env = os.environ.copy()
    env["COCOINDEX_DATABASE_URL"] = test_db_url
    env["OLLAMA_HOST"] = warmed_ollama

    # First index
    result1 = subprocess.run(
        [sys.executable, "-m", "cocosearch", "index", str(codebase), "--name", "incremental_test"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result1.returncode == 0

    # Modify one file
    (codebase / "file1.py").write_text("def foo(): return 42")

    # Re-index
    result2 = subprocess.run(
        [sys.executable, "-m", "cocosearch", "index", str(codebase), "--name", "incremental_test"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result2.returncode == 0

    # Parse stats from output or query database
    # Expected: 1 update, 0 insertions, 0 deletions
    # (Actual assertion depends on CLI output format)
```

### Pattern 4: Test Fixture Management

**What:** Minimal synthetic fixtures with predictable content

**When to use:** All E2E tests requiring test codebases

**Example:**
```python
# Source: pytest fixture best practices
import pytest
from pathlib import Path

@pytest.fixture
def e2e_test_codebase(tmp_path):
    """Create minimal test codebase with predictable search terms."""
    codebase = tmp_path / "e2e_fixture"
    codebase.mkdir()

    # Python sample with known search term "authentication"
    (codebase / "auth.py").write_text("""
def authenticate_user(username, password):
    '''User authentication logic.'''
    return check_credentials(username, password)
""")

    # Terraform sample
    (codebase / "main.tf").write_text("""
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"

  tags = {
    Name = "WebServer"
  }
}
""")

    # Dockerfile sample
    (codebase / "Dockerfile").write_text("""
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
""")

    # Shell script sample
    (codebase / "deploy.sh").write_text("""
#!/bin/bash
set -e
echo "Deploying application..."
docker build -t myapp .
docker push myapp:latest
""")

    return codebase
```

### Anti-Patterns to Avoid

- **Mocking subprocess calls**: E2E tests should run real CLI, not mock subprocess
- **In-process CLI invocation**: Bypasses argument parsing, entry point, exit codes
- **Parsing pretty output with regex**: Brittle; use JSON mode with structured assertions
- **Large real codebases as fixtures**: Slow, unpredictable results; use minimal synthetic data
- **Sharing test index names**: Use unique names per test or clean between tests
- **Hardcoded file paths**: Use tmp_path or relative paths from fixture root

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container lifecycle | Custom Docker API calls | testcontainers fixtures | Already implemented (Phase 12-13), handles cleanup, ports, healthchecks |
| JSON deep assertions | Manual nested dict access | jmespath or simple dict checks | jmespath cleaner but not required; manual is fine for shallow structure |
| Test data cleanup | Manual file deletion | pytest tmp_path fixture | Automatic cleanup, isolation, parallel-safe |
| Environment propagation | Manual env merging | os.environ.copy() + update | Standard pattern, prevents accidental leaks |

**Key insight:** E2E testing has well-established patterns. Don't reinvent subprocess invocation, JSON parsing, or fixture management. The complexity is in orchestrating real services, not in tooling.

## Common Pitfalls

### Pitfall 1: Environment Not Propagated to Subprocess

**What goes wrong:** Subprocess can't connect to test containers because COCOINDEX_DATABASE_URL not set

**Why it happens:** subprocess.run() uses clean environment by default, doesn't inherit pytest process env

**How to avoid:**
```python
env = os.environ.copy()  # Start with current env
env["COCOINDEX_DATABASE_URL"] = test_db_url  # Add container URL
env["OLLAMA_HOST"] = warmed_ollama
subprocess.run([...], env=env)  # Pass explicitly
```

**Warning signs:** "Connection refused" or "database not found" errors despite containers running

### Pitfall 2: JSON Parsing Before Exit Code Check

**What goes wrong:** Test tries to parse invalid JSON from failed command, gets confusing error

**Why it happens:** Failed commands may output error text, not JSON

**How to avoid:** Always check returncode before parsing output
```python
result = subprocess.run([...], capture_output=True, text=True)
assert result.returncode == 0, f"Command failed: {result.stderr}"
output = json.loads(result.stdout)  # Safe now
```

**Warning signs:** JSONDecodeError in tests when actual problem is command failure

### Pitfall 3: Reusing Index Names Across Tests

**What goes wrong:** Tests interfere with each other, unpredictable failures

**Why it happens:** Multiple tests index into same database table without cleanup

**How to avoid:** Use unique index names per test or clean between tests
```python
def test_something(test_db_url, warmed_ollama, request):
    index_name = f"test_{request.node.name}"  # Unique per test
    # Or use autouse fixture to clear all indexes between tests
```

**Warning signs:** Tests pass individually but fail when run together

### Pitfall 4: Asserting on Pretty Output Format

**What goes wrong:** Tests break when pretty output formatting changes

**Why it happens:** Rich/colored output format not stable API

**How to avoid:** Use JSON output mode for assertions, pretty mode only for manual verification
```python
# Bad:
assert "Indexed 42 files" in result.stdout

# Good:
output = json.loads(result.stdout)
assert output["files_indexed"] == 42
```

**Warning signs:** Tests fail after harmless formatting changes

### Pitfall 5: Missing text=True for JSON Parsing

**What goes wrong:** json.loads() fails because stdout is bytes, not str

**Why it happens:** subprocess returns bytes by default

**How to avoid:** Always use text=True when parsing text output
```python
result = subprocess.run([...], capture_output=True, text=True)  # ← text=True
output = json.loads(result.stdout)  # Works because stdout is str
```

**Warning signs:** TypeError about bytes vs str in json.loads()

## Code Examples

Verified patterns from official sources:

### Full Index-to-Search E2E Test
```python
# Source: Integration testing best practices + testcontainers
import subprocess
import sys
import os
import json
import pytest

@pytest.mark.integration
def test_full_indexing_and_search_flow(test_db_url, warmed_ollama, e2e_test_codebase):
    """End-to-end test: index codebase, search, verify results."""
    env = os.environ.copy()
    env["COCOINDEX_DATABASE_URL"] = test_db_url
    env["OLLAMA_HOST"] = warmed_ollama

    index_name = "e2e_full_flow"

    # Step 1: Index the codebase
    index_result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "index", str(e2e_test_codebase),
         "--name", index_name],
        capture_output=True,
        text=True,
        env=env,
    )

    assert index_result.returncode == 0, f"Indexing failed: {index_result.stderr}"

    # Step 2: Search for known content
    search_result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "search", "authentication logic",
         "--index", index_name],
        capture_output=True,
        text=True,
        env=env,
    )

    assert search_result.returncode == 0, f"Search failed: {search_result.stderr}"

    # Step 3: Validate search results
    results = json.loads(search_result.stdout)

    assert isinstance(results, list)
    assert len(results) > 0, "Should find at least one result"

    # Verify structure
    result = results[0]
    assert "filename" in result
    assert "start_line" in result
    assert "end_line" in result
    assert "score" in result

    # Verify we found the auth.py file
    assert "auth.py" in result["filename"]
    assert result["score"] > 0.5  # Reasonable similarity threshold
```

### DevOps File Validation
```python
# Source: Custom pattern for multi-language validation
@pytest.mark.integration
def test_devops_files_indexed_correctly(test_db_url, warmed_ollama, e2e_test_codebase):
    """Verify Terraform, Dockerfile, Bash all index with correct metadata."""
    env = os.environ.copy()
    env["COCOINDEX_DATABASE_URL"] = test_db_url
    env["OLLAMA_HOST"] = warmed_ollama

    index_name = "devops_validation"

    # Index
    subprocess.run(
        [sys.executable, "-m", "cocosearch", "index", str(e2e_test_codebase),
         "--name", index_name],
        capture_output=True,
        text=True,
        env=env,
        check=True,  # Raises on non-zero exit
    )

    # Test Terraform search with language filter
    tf_result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "search", "aws instance",
         "--index", index_name, "--lang", "terraform"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    tf_results = json.loads(tf_result.stdout)
    assert len(tf_results) > 0, "Should find Terraform results"
    assert any("main.tf" in r["filename"] for r in tf_results)

    # Test Dockerfile search
    docker_result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "search", "FROM python",
         "--index", index_name, "--lang", "dockerfile"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    docker_results = json.loads(docker_result.stdout)
    assert len(docker_results) > 0, "Should find Dockerfile results"
    assert any("Dockerfile" in r["filename"] for r in docker_results)

    # Test Bash search with alias
    bash_result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "search", "docker build",
         "--index", index_name, "--lang", "shell"],  # Alias for bash
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    bash_results = json.loads(bash_result.stdout)
    assert len(bash_results) > 0, "Should find shell script results"
    assert any("deploy.sh" in r["filename"] for r in bash_results)
```

### Exit Code and Error Message Validation
```python
# Source: CLI testing best practices
@pytest.mark.integration
def test_cli_error_handling(test_db_url, warmed_ollama):
    """Verify CLI returns proper exit codes and error messages."""
    env = os.environ.copy()
    env["COCOINDEX_DATABASE_URL"] = test_db_url
    env["OLLAMA_HOST"] = warmed_ollama

    # Test invalid path
    result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "index", "/nonexistent/path"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0, "Should fail for invalid path"
    assert "does not exist" in result.stderr or "Error" in result.stdout

    # Test missing query
    result = subprocess.run(
        [sys.executable, "-m", "cocosearch", "search", "--index", "test"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0, "Should fail without query"
    assert "Query required" in result.stdout or "error" in result.stdout.lower()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mocked subprocess | Real subprocess.run() | Always standard | E2E tests actually test CLI entry point |
| String output parsing | JSON output parsing | Modern CLI design (2020+) | Reliable structured assertions |
| Manual Docker management | testcontainers | 2020+ adoption | Automatic lifecycle, cleanup, port mapping |
| Large test fixtures | Minimal synthetic data | Testing best practices evolution | Faster, more predictable tests |
| Session-scoped everything | Function-scoped selectively | Performance vs isolation tradeoff | Balance speed and test isolation |

**Deprecated/outdated:**
- **pytest-subprocess for E2E**: Good for mocking, not for actual CLI integration testing
- **capfd/capsys for subprocess**: Only captures Python stdout, not subprocess output
- **Manual container port mapping**: testcontainers handles this automatically

## Open Questions

1. **JSON vs Pretty Output Testing**
   - What we know: Most tests should use JSON output for reliable assertions
   - What's unclear: Whether to test --pretty mode at all in E2E tests
   - Recommendation: Test JSON mode thoroughly; add 1-2 smoke tests for --pretty to ensure it doesn't crash

2. **Incremental Indexing Assertion Details**
   - What we know: CocoIndex returns IndexUpdateInfo with stats
   - What's unclear: Exact structure of stats dict for assertions
   - Recommendation: Examine CocoIndex return value in real test, document exact assertion pattern

3. **Fixture Complexity vs Coverage**
   - What we know: 5-10 files covers all language types
   - What's unclear: Optimal file size/complexity for realistic chunking
   - Recommendation: Start with simple files (10-30 lines each), add complexity only if chunking edge cases appear

## Sources

### Primary (HIGH confidence)

- [pytest subprocess testing best practices](https://docs.pytest.org/en/stable/example/simple.html) - Official pytest documentation
- [testcontainers Python guide](https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/) - Official testcontainers documentation
- [pytest subprocess patterns](https://github.com/rhcarvalho/pytest-subprocess-example) - Community best practices
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) - Official Python stdlib docs

### Secondary (MEDIUM confidence)

- [Integration testing with testcontainers](https://www.naiyerasif.com/post/2025/06/03/how-to-write-integration-tests-using-testcontainers-in-python/) - Recent 2025 guide
- [pytest JSON assertions](https://www.qabash.com/practical-json-patterns-api-to-assertions-in-pytest/) - Practical patterns
- [E2E testing best practices 2026](https://research.aimultiple.com/end-to-end-testing-best-practices/) - Industry best practices
- [pytest environment variables](https://pytest-with-eric.com/pytest-best-practices/pytest-environment-variables/) - Environment setup patterns

### Tertiary (LOW confidence)

- None - all findings verified with official documentation or recent (2025-2026) sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - subprocess, pytest, testcontainers all established in codebase
- Architecture: HIGH - Patterns verified in official docs and existing integration tests
- Pitfalls: HIGH - Common issues documented in pytest community, observable in existing tests

**Research date:** 2026-01-30
**Valid until:** 60 days (stable testing domain, patterns don't change rapidly)

**Notes:**
- Phases 12-13 already provide container fixtures (postgres_container, test_db_url, warmed_ollama)
- Existing integration test patterns from test_postgresql.py and test_ollama.py can be referenced
- CLI implementation in src/cocosearch/cli.py already has JSON output modes
- CocoIndex integration already proven in unit tests (mocked) and integration tests (real containers)
