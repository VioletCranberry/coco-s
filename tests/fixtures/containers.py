"""Container fixtures for integration testing.

Provides session-scoped PostgreSQL container using testcontainers-python.
Container starts once per test session and is reused across all integration tests.
"""

import os

import pytest
from testcontainers.postgres import PostgresContainer

# Environment variable configuration with defaults
TEST_DB_PORT = int(os.getenv("COCOSEARCH_TEST_DB_PORT", "5433"))
TEST_DB_USER = os.getenv("COCOSEARCH_TEST_DB_USER", "cocosearch_test")
TEST_DB_PASSWORD = os.getenv("COCOSEARCH_TEST_DB_PASSWORD", "test_password")
TEST_DB_NAME = os.getenv("COCOSEARCH_TEST_DB_NAME", "cocosearch_test")


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for entire test session.

    Locked decisions from Phase 12 CONTEXT:
    - Session scope (one container for all tests)
    - 60s timeout (handles slow CI, first pull)
    - Pin pg16 (reproducible, explicit upgrades)
    - Port 5433 (avoid local PostgreSQL on 5432)
    """
    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        port=5432,  # Internal port, testcontainers maps to random external port
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        dbname=TEST_DB_NAME,
    ).with_env("POSTGRES_HOST_AUTH_METHOD", "trust") as postgres:
        # Wait for container ready (testcontainers handles this automatically)
        yield postgres


@pytest.fixture(scope="session")
def test_db_url(postgres_container):
    """Get connection URL for test database.

    Returns psycopg3-compatible connection URL.
    """
    return postgres_container.get_connection_url(driver=None)
