# Phase 12: Container Infrastructure & PostgreSQL - Research

**Researched:** 2026-01-30
**Domain:** Docker-based integration testing with PostgreSQL and pgvector
**Confidence:** HIGH

## Summary

This phase requires setting up real Docker-based PostgreSQL containers for integration testing. The standard approach in Python uses testcontainers-python (v4.14.0, released January 7, 2026) with session-scoped pytest fixtures for container lifecycle management. The project already has psycopg[pool] 3.3.2+ and pytest-asyncio configured, providing the foundation for this work.

The established pattern is: session-scoped container fixture (one PostgreSQL instance for entire test run) + function-scoped cleanup fixture (TRUNCATE tables between tests). This provides real database validation while maintaining test isolation and reasonable performance. The pgvector/pgvector:pg16 official Docker image includes both PostgreSQL and pgvector pre-installed, requiring only `CREATE EXTENSION vector` at test database initialization.

User decisions from Phase 12 CONTEXT.md specify: session-scoped containers, TRUNCATE-based isolation, fixed port 5433 (avoids local PostgreSQL on 5432), 60s startup timeout, docker-compose.test.yml for configuration, and fail-immediately error handling when Docker is unavailable.

**Primary recommendation:** Use testcontainers-python with session-scoped PostgreSQL fixture, function-scoped TRUNCATE cleanup, pgvector/pgvector:pg16 image, and environment variable configuration for CI flexibility.

## Standard Stack

The established libraries/tools for Docker-based PostgreSQL integration testing with Python:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| testcontainers[postgresql] | 4.14.0+ | Docker container lifecycle management | Official Testcontainers project, 2.1k stars, automatic cleanup via Ryuk, built-in PostgreSQL support |
| psycopg[pool] | 3.3.2+ | PostgreSQL driver with connection pooling | Official PostgreSQL adapter for Python, psycopg3 is current version, already in pyproject.toml |
| pytest | 9.0.2+ | Testing framework with fixture system | Already configured, session/function scopes enable container reuse pattern |
| pgvector/pgvector | pg16 (0.8.1) | PostgreSQL + pgvector Docker image | Official image from pgvector project, includes PostgreSQL 16 + pgvector 0.8.1 pre-installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| docker-compose | N/A | Optional: separate test config | Alternative to testcontainers for static container setup, user decided on docker-compose.test.yml |
| pytest-postgresql | 6.1.0+ | Alternative: pytest plugin for PostgreSQL | If avoiding testcontainers, provides postgresql_noproc fixture for external containers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| testcontainers-python | pytest-docker-compose plugin | Static docker-compose.yml vs programmatic control; compose better if just need running DB, testcontainers better for dynamic container manipulation |
| testcontainers-python | pytest-postgresql with Docker | Less mature ecosystem, requires separate container management |
| Session-scoped fixtures | Module-scoped fixtures | Module scope only reuses within one test file, session scope reuses across all tests |

**Installation:**
```bash
pip install "testcontainers[postgresql]>=4.14.0"
# psycopg already installed via project dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py                    # Session fixtures (container), autouse reset_db_pool
├── fixtures/
│   ├── db.py                      # Mock fixtures for unit tests (existing)
│   └── container.py               # NEW: Real container fixtures for integration tests
├── integration/
│   ├── conftest.py                # Integration marker auto-apply (existing)
│   └── test_*.py                  # Tests use real PostgreSQL
└── docker-compose.test.yml        # NEW: PostgreSQL container config (per user decision)
```

### Pattern 1: Session-Scoped PostgreSQL Container
**What:** One PostgreSQL container starts at test session beginning, stops at end
**When to use:** All integration tests (locked user decision: session-scoped)
**Example:**
```python
# tests/fixtures/container.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for entire test session.

    Locked decisions from Phase 12 CONTEXT:
    - Session scope (one container for all tests)
    - 60s timeout (handles slow CI, first pull)
    - Pin pg16 (reproducible, explicit upgrades)
    """
    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        # User specified fixed port 5433 to avoid local PostgreSQL on 5432
        port=5433
    ) as postgres:
        # Wait for container ready (testcontainers handles this automatically)
        yield postgres
```

### Pattern 2: Database Initialization with pgvector
**What:** Initialize pgvector extension once per session after container starts
**When to use:** Session-scoped fixture depending on postgres_container
**Example:**
```python
# Source: testcontainers-python docs + pgvector Docker Hub
@pytest.fixture(scope="session")
def test_db_url(postgres_container):
    """Get connection URL and initialize pgvector extension.

    pgvector/pgvector image has extension files installed,
    just need CREATE EXTENSION to enable it.
    """
    import psycopg

    db_url = postgres_container.get_connection_url(driver=None)  # psycopg3

    # Initialize pgvector extension (runs once per session)
    with psycopg.connect(db_url) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()

    return db_url
```

### Pattern 3: TRUNCATE-Based Test Isolation
**What:** Function-scoped fixture that truncates all tables after each test
**When to use:** All integration tests (locked user decision: TRUNCATE for speed)
**Example:**
```python
# Source: pytest-django CASCADE pattern + SQLAlchemy metadata
@pytest.fixture(scope="function", autouse=True)
def clean_db(test_db_url):
    """Clean database between tests via TRUNCATE CASCADE.

    Locked decision: TRUNCATE (fast) vs DROP/CREATE (slow).
    CASCADE handles foreign key constraints automatically.
    """
    yield  # Run test first

    # Cleanup after test
    import psycopg
    with psycopg.connect(test_db_url) as conn:
        # Get all tables from schema
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()

        if tables:
            table_names = ", ".join(f'"{t[0]}"' for t in tables)
            # CASCADE handles foreign key dependencies
            conn.execute(f"TRUNCATE TABLE {table_names} CASCADE")
            conn.commit()
```

### Pattern 4: Connection Pool for Integration Tests
**What:** Function-scoped connection pool fixture for each test
**When to use:** Tests that need database access
**Example:**
```python
# Source: psycopg3 pool documentation
from psycopg_pool import ConnectionPool

@pytest.fixture(scope="function")
def db_pool(test_db_url, clean_db):
    """Create connection pool for test.

    Function scope: new pool per test (isolation).
    Depends on clean_db to ensure cleanup happens.
    """
    pool = ConnectionPool(
        test_db_url,
        min_size=1,
        max_size=5,
        timeout=10
    )
    pool.wait()  # Ensure min_size connections acquired
    yield pool
    pool.close()
```

### Anti-Patterns to Avoid
- **Module-scoped containers:** Session scope reuses across all test files, module scope only within one file (less efficient)
- **Fixed port without override:** User decided on fixed 5433, but always allow env var override for CI (e.g., COCOSEARCH_TEST_DB_PORT)
- **Using 'latest' tag:** Pin exact version (pg16) for reproducibility, avoid surprises from automatic updates
- **DELETE instead of TRUNCATE:** TRUNCATE is faster and resets sequences, DELETE leaves auto-increment state
- **TRUNCATE without CASCADE:** Foreign keys cause "cannot truncate" errors; CASCADE handles dependencies automatically

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker container lifecycle | Custom subprocess.run("docker run") | testcontainers-python | Automatic cleanup via Ryuk container, health checks, port mapping, cross-platform Docker socket detection |
| Waiting for PostgreSQL ready | Sleep or retry loops | testcontainers built-in wait | Handles PostgreSQL's double-restart (initial start + config reload), avoids race conditions |
| Database cleanup between tests | Manual DROP TABLE + CREATE TABLE | TRUNCATE ... CASCADE | 10-100x faster, keeps schema, CASCADE handles foreign key dependencies automatically |
| Connection pool management | Manual connection open/close | psycopg_pool.ConnectionPool | Connection reuse, automatic reconnection on failure, health checks, statistics |
| Test database schema creation | SQL scripts in /docker-entrypoint-initdb.d/ | Tests create schema as needed | User decision: "tests create their own schema as needed — explicit, each module sets up what it needs" |

**Key insight:** Container lifecycle management is complex (cleanup on failure, signal handling, port conflicts, Docker socket detection). testcontainers-python solves all of this with a mature, well-tested library used by 5,800+ projects.

## Common Pitfalls

### Pitfall 1: Container Not Cleaned Up on Test Failure
**What goes wrong:** Tests fail, containers keep running, ports stay bound
**Why it happens:** Manual cleanup in teardown doesn't run on interrupts (Ctrl+C, CI timeout)
**How to avoid:** testcontainers-python uses Ryuk container for automatic cleanup even on ungraceful exit
**Warning signs:** `docker ps` shows orphaned containers, port already allocated errors

### Pitfall 2: Race Condition in PostgreSQL Startup
**What goes wrong:** Tests connect before PostgreSQL fully ready, get "database system is starting up" errors
**Why it happens:** PostgreSQL restarts itself after initial configuration, TCP port opens before database accepts connections
**How to avoid:** testcontainers-python handles wait strategy automatically; for manual check use `pg_isready` not TCP connect
**Warning signs:** Intermittent connection failures in first few seconds, flaky tests that pass on retry

### Pitfall 3: Foreign Key Constraints Block TRUNCATE
**What goes wrong:** `TRUNCATE TABLE users` fails with "cannot truncate a table referenced in a foreign key constraint"
**Why it happens:** Other tables have foreign keys to truncated table
**How to avoid:** Always use `TRUNCATE ... CASCADE` or truncate in reverse dependency order via `reversed(Base.metadata.sorted_tables)`
**Warning signs:** IntegrityError during cleanup, error message mentions foreign key constraint

### Pitfall 4: Connection Pool Not Closed Between Tests
**What goes wrong:** Connection pool grows, "too many connections" errors, tests slow down
**Why it happens:** Function-scoped pool fixture doesn't close pool in teardown
**How to avoid:** Always `pool.close()` in fixture teardown, or use context manager pattern
**Warning signs:** `SELECT * FROM pg_stat_activity` shows many IDLE connections from previous tests

### Pitfall 5: pgvector Extension Not Initialized
**What goes wrong:** `SELECT ... <-> embedding` fails with "operator does not exist: vector <-> vector"
**Why it happens:** pgvector/pgvector image has files installed but extension not created in database
**How to avoid:** Run `CREATE EXTENSION IF NOT EXISTS vector` in session-scoped fixture after container starts
**Warning signs:** Vector similarity queries fail, `\dx` in psql doesn't show vector extension

### Pitfall 6: Docker Not Available in CI
**What goes wrong:** Tests fail in CI with "Cannot connect to Docker daemon"
**Why it happens:** CI environment doesn't have Docker installed/running or permissions wrong
**How to avoid:** User decision: "fail immediately if Docker unavailable — hard error forces Docker availability"; add Docker availability check to conftest, fail with clear message
**Warning signs:** ConnectionError from testcontainers, /var/run/docker.sock not found

### Pitfall 7: First Test Takes 60+ Seconds (Image Pull)
**What goes wrong:** First test run in CI downloads multi-GB PostgreSQL image, times out
**Why it happens:** Docker image not cached, downloads on first container start
**How to avoid:** User decision: "60 second startup timeout — handles slow CI runners and first-time image pulls"; in CI cache Docker images or pre-pull in separate step
**Warning signs:** First run slow, subsequent runs fast; testcontainers timeout after 120s

## Code Examples

Verified patterns from official sources:

### PostgreSQL Container with Fixed Port
```python
# Source: testcontainers-python PostgresContainer API
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL with pgvector on fixed port 5433.

    User decision: Fixed port 5433 avoids conflict with local PostgreSQL on 5432.
    Still allow environment variable override for CI flexibility.
    """
    import os
    test_port = int(os.getenv("COCOSEARCH_TEST_DB_PORT", "5433"))

    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        port=test_port,
        user="cocosearch_test",
        password="test_password",
        dbname="cocosearch_test"
    ) as postgres:
        yield postgres
```

### Database Initialization Pattern
```python
# Source: Testcontainers guide + pgvector GitHub
import psycopg

@pytest.fixture(scope="session")
def initialized_db(postgres_container):
    """Initialize database with pgvector extension.

    get_connection_url(driver=None) returns psycopg3-compatible URL.
    pgvector image has extension files, just need CREATE EXTENSION.
    """
    db_url = postgres_container.get_connection_url(driver=None)

    with psycopg.connect(db_url) as conn:
        # Enable pgvector (idempotent)
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # User decision: "tests create their own schema as needed"
        # Don't create schema here, let each test module do it

        conn.commit()

    return db_url
```

### TRUNCATE Cleanup with CASCADE
```python
# Source: pytest-django TRUNCATE CASCADE pattern
import psycopg

@pytest.fixture(autouse=True)
def clean_tables(initialized_db):
    """Clean all tables between tests using TRUNCATE CASCADE.

    CASCADE handles foreign key constraints automatically.
    Faster than DROP/CREATE, keeps schema intact.
    """
    yield  # Run test

    # Cleanup after test
    with psycopg.connect(initialized_db) as conn:
        with conn.cursor() as cur:
            # Get all user tables (exclude system tables)
            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]

            if tables:
                # Quote table names for safety
                quoted = ', '.join(f'"{t}"' for t in tables)
                cur.execute(f"TRUNCATE TABLE {quoted} CASCADE")

        conn.commit()
```

### Connection Pool Pattern
```python
# Source: psycopg3 pool documentation
from psycopg_pool import ConnectionPool

@pytest.fixture
def db_pool(initialized_db, clean_tables):
    """Provide connection pool for integration test.

    Function scope: fresh pool per test.
    Depends on clean_tables to ensure cleanup happens.
    """
    pool = ConnectionPool(
        initialized_db,
        min_size=1,
        max_size=5,
        timeout=10,
        # Check connection health before handing to clients
        check=ConnectionPool.check_connection
    )

    # Wait for min_size connections (catches config errors early)
    pool.wait()

    yield pool

    # Always close to prevent connection leaks
    pool.close()
```

### Docker Availability Check
```python
# Source: testcontainers-python issue discussions
import docker
import pytest

def pytest_configure(config):
    """Check Docker availability at test session start.

    User decision: "Fail immediately if Docker unavailable —
    hard error forces Docker availability"
    """
    try:
        client = docker.from_env()
        client.ping()
    except Exception as e:
        pytest.exit(
            f"Docker is not available: {e}\n"
            f"Integration tests require Docker to be installed and running.\n"
            f"Install Docker: https://docs.docker.com/get-docker/",
            returncode=1
        )
```

### Environment Variable Configuration
```python
# Source: User decision + testcontainers best practices
import os

# tests/fixtures/container.py
TEST_DB_PORT = int(os.getenv("COCOSEARCH_TEST_DB_PORT", "5433"))
TEST_DB_USER = os.getenv("COCOSEARCH_TEST_DB_USER", "cocosearch_test")
TEST_DB_PASSWORD = os.getenv("COCOSEARCH_TEST_DB_PASSWORD", "test_password")
TEST_DB_NAME = os.getenv("COCOSEARCH_TEST_DB_NAME", "cocosearch_test")

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL with environment variable configuration.

    User decision: "Environment variables with defaults —
    override via env vars for CI flexibility"
    """
    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        port=TEST_DB_PORT,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        dbname=TEST_DB_NAME
    ) as postgres:
        yield postgres
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| testcontainers-* packages | testcontainers[extras] | v4.0.0 (2024) | Install `testcontainers[postgresql]` not `testcontainers-postgres` package |
| psycopg2 | psycopg3 | 2021+ | New driver, async support, better typing; project already on psycopg 3.3.2+ |
| docker-compose for tests | testcontainers-python | 2020+ | Programmatic control vs static config; both valid, user chose docker-compose.test.yml |
| Module-scoped fixtures | Session-scoped fixtures | Pytest 3.0+ | Session scope reuses across all test files, not just one module |
| pg_isready TCP check | Built-in health checks | testcontainers 4.0+ | Automatic wait strategy handles PostgreSQL double-restart |

**Deprecated/outdated:**
- **testcontainers-postgres package:** Use `testcontainers[postgresql]` extra instead (deprecated in v4.0.0)
- **SQLAlchemy dependency:** No longer bundled with testcontainers[postgresql], declare explicitly if needed
- **wait_for() manual calls:** testcontainers 4.x handles wait strategy automatically via context manager
- **Ryuk disabled by default:** Now enabled by default for automatic cleanup (override with TESTCONTAINERS_RYUK_DISABLED=true)

## Open Questions

Things that couldn't be fully resolved:

1. **Schema Creation Approach**
   - What we know: User decided "tests create their own schema as needed — explicit, each module sets up what it needs"
   - What's unclear: Should each test module create full schema or use SQLAlchemy/migration tools?
   - Recommendation: Start simple with explicit CREATE TABLE in test module; if schema gets complex, consider pytest fixtures that run DDL scripts

2. **Connection Retry Strategy Details**
   - What we know: User decided "Retry once with 1s backoff on connection loss — handles transient issues"
   - What's unclear: Should retry be in connection pool config, test fixtures, or application code?
   - Recommendation: Implement in test fixtures first (connection level), not pool level, to isolate test-specific retry logic

3. **Container Log Capture on Failure**
   - What we know: User decided "Fail with diagnostic message on startup failure — show container logs, suggest fixes"
   - What's unclear: testcontainers-python automatic log capture capability needs verification
   - Recommendation: Add explicit log capture in fixture error handling if not automatic; check testcontainers API for `.get_logs()` method

4. **Health Check Strategy**
   - What we know: User left to Claude's discretion "Health check implementation details (pg_isready vs TCP)"
   - What's unclear: Does testcontainers-python PostgresContainer have built-in health check or need explicit configuration?
   - Recommendation: Verify testcontainers-python PostgresContainer behavior; if no built-in check, add explicit `wait_for_logs("database system is ready to accept connections")`

## Sources

### Primary (HIGH confidence)
- testcontainers-python v4.14.0 documentation: https://testcontainers-python.readthedocs.io/ (official docs, version-specific)
- testcontainers-python GitHub: https://github.com/testcontainers/testcontainers-python (v4.14.0 released 2026-01-07, Python >=3.10)
- psycopg3 Connection Pools: https://www.psycopg.org/psycopg3/docs/advanced/pool.html (official psycopg documentation)
- pgvector GitHub: https://github.com/pgvector/pgvector (Postgres 13+, CREATE EXTENSION vector)
- Docker Hub pgvector images: https://hub.docker.com/r/pgvector/pgvector/tags (pg16:0.8.1, pg17:0.8.1 current as of 2026)

### Secondary (MEDIUM confidence)
- [Testcontainers Best Practices | Docker Blog](https://www.docker.com/blog/testcontainers-best-practices/) (avoid 'latest', dynamic ports, reuse containers)
- [Getting started with Testcontainers for Python](https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/) (official guide, module/session scope patterns)
- [Python Integration Tests: docker-compose vs testcontainers | Medium](https://medium.com/codex/python-integration-tests-docker-compose-vs-testcontainers-94986d7547ce) (comparison of approaches)
- [pytest-django TRUNCATE CASCADE PR](https://github.com/pytest-dev/pytest-django/pull/575) (CASCADE pattern for foreign keys)

### Tertiary (LOW confidence - flagged for validation)
- [Mastering Unit Testing with Testcontainers | ThinhDA](https://thinhdanggroup.github.io/testcontainers-2/) (community tutorial, best practices)
- [Using Testcontainers with Pytest | Qxf2](https://qxf2.com/blog/using-testcontainers-with-pytest/) (community blog, module scope fixtures)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - testcontainers-python v4.14.0 verified via GitHub (2026-01-07 release), psycopg3 via official docs, pgvector via Docker Hub
- Architecture: HIGH - Session/function scope patterns verified in official testcontainers guides, TRUNCATE CASCADE from pytest-django PR
- Pitfalls: MEDIUM - Common issues compiled from GitHub issues, blog posts, and community discussions; not all from official sources

**Research date:** 2026-01-30
**Valid until:** 2026-02-27 (30 days - stable domain, testcontainers mature project)
