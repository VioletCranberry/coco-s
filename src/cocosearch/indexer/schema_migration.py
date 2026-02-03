"""Schema migration for hybrid search columns.

Adds PostgreSQL-specific columns and indexes that CocoIndex doesn't support natively:
- content_tsv: TSVECTOR generated column from content_tsv_input
- GIN index on content_tsv for fast keyword search
"""

import logging
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def ensure_hybrid_search_schema(conn: psycopg.Connection, table_name: str) -> dict[str, Any]:
    """Ensure hybrid search columns and indexes exist on a table.

    This is idempotent - safe to call multiple times.

    Args:
        conn: PostgreSQL connection
        table_name: Name of the chunks table (e.g., "myindex_chunks")

    Returns:
        Dict with migration results:
        - tsvector_added: bool - whether column was added
        - gin_index_added: bool - whether index was created
        - already_exists: bool - whether schema was already complete
    """
    results = {
        "tsvector_added": False,
        "gin_index_added": False,
        "already_exists": False,
    }

    with conn.cursor() as cur:
        # Check if content_tsv column exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'content_tsv'
        """, (table_name,))
        tsvector_exists = cur.fetchone() is not None

        # Check if GIN index exists
        index_name = f"idx_{table_name}_content_tsv"
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = %s AND indexname = %s
        """, (table_name, index_name))
        gin_exists = cur.fetchone() is not None

        if tsvector_exists and gin_exists:
            results["already_exists"] = True
            logger.info(f"Hybrid search schema already complete for {table_name}")
            return results

        # Add TSVECTOR generated column if missing
        if not tsvector_exists:
            logger.info(f"Adding content_tsv column to {table_name}")
            cur.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN content_tsv TSVECTOR
                GENERATED ALWAYS AS (to_tsvector('simple', COALESCE(content_tsv_input, ''))) STORED
            """)
            results["tsvector_added"] = True
            conn.commit()

        # Create GIN index if missing
        if not gin_exists:
            logger.info(f"Creating GIN index on {table_name}.content_tsv")
            # Use CONCURRENTLY to avoid locking the table (requires autocommit)
            # For safety, we don't use CONCURRENTLY here - run during maintenance window
            cur.execute(f"""
                CREATE INDEX {index_name} ON {table_name} USING GIN (content_tsv)
            """)
            results["gin_index_added"] = True
            conn.commit()

    logger.info(f"Hybrid search schema migration complete for {table_name}: {results}")
    return results


def verify_hybrid_search_schema(conn: psycopg.Connection, table_name: str) -> bool:
    """Verify hybrid search schema is properly configured.

    Args:
        conn: PostgreSQL connection
        table_name: Name of the chunks table

    Returns:
        True if schema is complete and functional
    """
    with conn.cursor() as cur:
        # Verify tsvector column exists and is correct type
        cur.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'content_tsv'
        """, (table_name,))
        col = cur.fetchone()
        if not col or col[0] != 'tsvector':
            return False

        # Verify GIN index exists
        index_name = f"idx_{table_name}_content_tsv"
        cur.execute("""
            SELECT indexdef
            FROM pg_indexes
            WHERE tablename = %s AND indexname = %s
        """, (table_name, index_name))
        idx = cur.fetchone()
        if not idx or 'gin' not in idx[0].lower():
            return False

        return True


def ensure_symbol_columns(conn: psycopg.Connection, table_name: str) -> dict[str, Any]:
    """Ensure symbol metadata columns exist on a table.

    This is idempotent - safe to call multiple times.
    Adds nullable TEXT columns (no default value) for backward compatibility.

    Args:
        conn: PostgreSQL connection
        table_name: Name of the chunks table (e.g., "myindex_chunks")

    Returns:
        Dict with migration results:
        - columns_added: list of column names added
        - already_exists: bool if all columns existed
    """
    results = {
        "columns_added": [],
        "already_exists": False,
    }

    symbol_columns = ["symbol_type", "symbol_name", "symbol_signature"]

    with conn.cursor() as cur:
        # Check which columns exist
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = ANY(%s)
        """, (table_name, symbol_columns))
        existing = {row[0] for row in cur.fetchall()}

        if len(existing) == len(symbol_columns):
            results["already_exists"] = True
            logger.info(f"Symbol columns already exist for {table_name}")
            return results

        # Add missing columns as TEXT NULL
        for col in symbol_columns:
            if col not in existing:
                logger.info(f"Adding {col} column to {table_name}")
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} TEXT NULL")
                results["columns_added"].append(col)

        conn.commit()

    logger.info(f"Symbol schema migration complete for {table_name}: {results}")
    return results


def verify_symbol_columns(conn: psycopg.Connection, table_name: str) -> bool:
    """Verify symbol columns exist on a table.

    Args:
        conn: PostgreSQL connection
        table_name: Name of the chunks table

    Returns:
        True if all symbol columns exist
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name IN ('symbol_type', 'symbol_name', 'symbol_signature')
        """, (table_name,))
        existing = {row[0] for row in cur.fetchall()}
        return len(existing) == 3
