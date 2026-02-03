"""Index statistics module for cocosearch.

Provides functions to retrieve storage and content statistics
for indexed codebases.
"""

from cocosearch.search.db import get_connection_pool, get_table_name


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string.

    Args:
        size: Size in bytes.

    Returns:
        Human-readable string (e.g., "1.5 MB", "256 KB").
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


def get_stats(index_name: str) -> dict:
    """Get statistics for an index.

    Args:
        index_name: The name of the index.

    Returns:
        Dict with keys:
        - name: Index name
        - file_count: Number of unique files indexed
        - chunk_count: Total number of chunks
        - storage_size: Storage size in bytes
        - storage_size_pretty: Human-readable storage size

    Raises:
        ValueError: If the index does not exist.
    """
    pool = get_connection_pool()
    table_name = get_table_name(index_name)

    # First verify the table exists
    check_query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        )
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(check_query, (table_name,))
            (exists,) = cur.fetchone()

            if not exists:
                raise ValueError(f"Index '{index_name}' not found")

            # Get file count and chunk count
            stats_query = f"""
                SELECT
                    COUNT(DISTINCT filename) as file_count,
                    COUNT(*) as chunk_count
                FROM {table_name}
            """
            cur.execute(stats_query)
            file_count, chunk_count = cur.fetchone()

            # Get storage size
            size_query = "SELECT pg_table_size(%s)"
            cur.execute(size_query, (table_name,))
            (storage_size,) = cur.fetchone()

    return {
        "name": index_name,
        "file_count": file_count,
        "chunk_count": chunk_count,
        "storage_size": storage_size,
        "storage_size_pretty": format_bytes(storage_size),
    }


def get_language_stats(index_name: str) -> list[dict]:
    """Get per-language statistics for an index.

    Uses SQL GROUP BY for efficient aggregation at database level.
    Gracefully handles pre-v1.7 indexes that lack content_text column.

    Args:
        index_name: The name of the index.

    Returns:
        List of dicts with keys:
        - language: Language identifier (e.g., "python", "hcl")
        - file_count: Number of unique files for this language
        - chunk_count: Number of chunks for this language
        - line_count: Number of lines (None if pre-v1.7 index)

        List is sorted by chunk_count descending.

    Raises:
        ValueError: If the index does not exist.
    """
    pool = get_connection_pool()
    table_name = get_table_name(index_name)

    # First verify the table exists
    check_query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        )
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(check_query, (table_name,))
            (exists,) = cur.fetchone()

            if not exists:
                raise ValueError(f"Index '{index_name}' not found")

            # Check if content_text column exists (v1.7+)
            col_check = """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'content_text'
            """
            cur.execute(col_check, (table_name,))
            has_content_text = cur.fetchone() is not None

            # Build query with conditional line count
            if has_content_text:
                stats_query = f"""
                    SELECT
                        COALESCE(language_id, 'unknown') as language,
                        COUNT(DISTINCT filename) as file_count,
                        COUNT(*) as chunk_count,
                        SUM(array_length(string_to_array(content_text, E'\\n'), 1)) as line_count
                    FROM {table_name}
                    GROUP BY language_id
                    ORDER BY chunk_count DESC
                """
            else:
                # Graceful degradation for pre-v1.7 indexes
                stats_query = f"""
                    SELECT
                        COALESCE(language_id, 'unknown') as language,
                        COUNT(DISTINCT filename) as file_count,
                        COUNT(*) as chunk_count,
                        NULL as line_count
                    FROM {table_name}
                    GROUP BY language_id
                    ORDER BY chunk_count DESC
                """

            cur.execute(stats_query)
            rows = cur.fetchall()

            return [
                {
                    "language": row[0] if row[0] else "unknown",
                    "file_count": row[1],
                    "chunk_count": row[2],
                    "line_count": row[3],
                }
                for row in rows
            ]
