# Phase 4: Index Management - Research

**Researched:** 2026-01-25
**Domain:** MCP Server Implementation, PostgreSQL Index Management, CLI Extensions
**Confidence:** HIGH

## Summary

Phase 4 extends the existing cocosearch CLI with management commands (list, stats, clear) and adds an MCP server for LLM integration. The MCP Python SDK (v1.26.0) is already installed as a dependency, providing `FastMCP` for simple server creation with the `@mcp.tool()` decorator. PostgreSQL metadata queries will be used for listing indexes and gathering statistics.

The architecture follows a clean separation: reusable management functions in a new `management/` module, CLI commands calling these functions with formatting, and MCP tools calling the same functions with JSON responses. The MCP server runs via stdio transport, launched by `cocosearch mcp` subcommand.

**Primary recommendation:** Implement management functions first, then add CLI commands, finally expose via MCP server. Use PostgreSQL `information_schema.tables` for index discovery and `pg_table_size()` for storage metrics.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mcp | 1.26.0 | MCP server framework | Already installed, official SDK with FastMCP |
| psycopg | 3.3.2 | PostgreSQL queries | Already used for search, connection pool exists |
| argparse | stdlib | CLI parsing | Already used, no additional dependencies |
| subprocess | stdlib | Git operations | Lightweight, no external package needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich | 13.0.0 | Pretty output formatting | Already used for --pretty flag |
| logging | stdlib | MCP server logging (stderr) | Required for stdio transport |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess for git | GitPython | Adds dependency for single command; subprocess sufficient |
| information_schema | pg_catalog | information_schema more portable, both work |

**Installation:**
No new dependencies required. All packages already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
src/cocosearch/
├── management/          # NEW: Index management functions
│   ├── __init__.py     # Exports: list_indexes, get_stats, clear_index
│   ├── discovery.py    # Index discovery from PostgreSQL
│   ├── stats.py        # Statistics gathering
│   └── git.py          # Git root detection utility
├── mcp/                 # NEW: MCP server implementation
│   ├── __init__.py     # Exports: create_server, run_server
│   └── server.py       # FastMCP server with tools
├── indexer/            # Existing
├── search/             # Existing
└── cli.py              # Extended with list, stats, clear, mcp commands
```

### Pattern 1: Shared Management Functions
**What:** Core business logic in management module, consumed by both CLI and MCP
**When to use:** Any operation that needs both CLI and MCP access
**Example:**
```python
# src/cocosearch/management/discovery.py
# Source: PostgreSQL documentation + existing db.py pattern

def list_indexes() -> list[dict]:
    """List all cocosearch indexes with basic info.

    Returns list of dicts with keys: name, table_name, exists
    """
    pool = get_connection_pool()
    # Find tables matching CocoIndex naming pattern
    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE 'codeindex_%__%_chunks'
        ORDER BY table_name
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    # Extract index names from table names
    # Pattern: codeindex_{name}__{name}_chunks
    indexes = []
    for (table_name,) in rows:
        # Parse: codeindex_myproject__myproject_chunks -> myproject
        parts = table_name.split('__')
        if len(parts) == 2:
            name = parts[0].replace('codeindex_', '')
            indexes.append({
                'name': name,
                'table_name': table_name,
            })
    return indexes
```

### Pattern 2: MCP Server with FastMCP
**What:** Use `@mcp.tool()` decorator for tool registration
**When to use:** All MCP tool definitions
**Example:**
```python
# src/cocosearch/mcp/server.py
# Source: https://modelcontextprotocol.io/docs/develop/build-server

import logging
from mcp.server.fastmcp import FastMCP

from cocosearch.management import list_indexes, get_stats, clear_index
from cocosearch.search import search

# Configure logging to stderr (CRITICAL for stdio transport)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("cocosearch")

@mcp.tool()
def search_code(query: str, index_name: str, limit: int = 10) -> list[dict]:
    """Search indexed code using natural language.

    Args:
        query: Natural language search query
        index_name: Name of the index to search
        limit: Maximum results to return (default 10)
    """
    results = search(query=query, index_name=index_name, limit=limit)
    return [
        {
            "file": r.filename,
            "start_line": r.start_byte,  # Will need line conversion
            "end_line": r.end_byte,
            "score": r.score,
            "content": read_chunk_content(r),  # Include actual code
        }
        for r in results
    ]

@mcp.tool()
def list_indexes() -> list[dict]:
    """List all available code indexes."""
    return list_indexes()

def run_server():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")
```

### Pattern 3: Git Root Detection
**What:** Auto-detect index name from git repository root
**When to use:** When no --index specified and inside a git repo
**Example:**
```python
# src/cocosearch/management/git.py
# Source: https://git-scm.com/docs/git-rev-parse

import subprocess
from pathlib import Path

def get_git_root() -> Path | None:
    """Get the root directory of the current git repository.

    Returns:
        Path to git root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None  # Not in a git repo

def derive_index_from_git() -> str | None:
    """Derive index name from git repository root directory name.

    Returns:
        Index name derived from git root, or None if not in a repo.
    """
    git_root = get_git_root()
    if git_root is None:
        return None
    # Reuse existing derive_index_name function
    from cocosearch.cli import derive_index_name
    return derive_index_name(str(git_root))
```

### Pattern 4: Statistics with PostgreSQL Metadata
**What:** Gather index statistics using PostgreSQL system catalogs
**When to use:** For stats command and MCP stats tool
**Example:**
```python
# src/cocosearch/management/stats.py
# Source: https://neon.com/postgresql/postgresql-administration/postgresql-database-indexes-table-size

from datetime import datetime

def get_index_stats(index_name: str) -> dict:
    """Get statistics for a specific index.

    Returns dict with:
        - file_count: Number of unique files indexed
        - chunk_count: Total number of chunks
        - storage_size: Storage size in bytes
        - storage_size_pretty: Human-readable size
        - last_indexed: Timestamp (if available)
    """
    pool = get_connection_pool()
    table_name = get_table_name(index_name)

    sql = """
        SELECT
            COUNT(DISTINCT filename) as file_count,
            COUNT(*) as chunk_count,
            pg_table_size(%s) as storage_bytes
        FROM {table}
    """.format(table=table_name)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, [table_name])
            row = cur.fetchone()

            if row is None:
                raise ValueError(f"Index '{index_name}' not found")

            file_count, chunk_count, storage_bytes = row

    return {
        'name': index_name,
        'file_count': file_count,
        'chunk_count': chunk_count,
        'storage_size': storage_bytes,
        'storage_size_pretty': format_bytes(storage_bytes),
    }

def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
```

### Anti-Patterns to Avoid
- **Logging to stdout in MCP server:** Corrupts JSON-RPC protocol. Always use stderr via `logging` module.
- **Blocking calls without async:** MCP server should use async functions for I/O operations.
- **Hardcoded table patterns:** Table names follow CocoIndex convention; use `get_table_name()` utility.
- **Silent failures on infrastructure:** Always return clear error messages if Postgres/Ollama unavailable.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git root detection | Walk directories for .git | `git rev-parse --show-toplevel` | Handles symlinks, worktrees, bare repos |
| Table size calculation | Count bytes manually | `pg_table_size()` | Accurate, includes TOAST and FSM |
| MCP protocol handling | Custom JSON-RPC | `mcp.server.fastmcp.FastMCP` | Handles transport, schema generation |
| Connection pooling | Create connections per request | Existing `get_connection_pool()` | Already implemented, handles cleanup |
| Index name sanitization | Custom regex | Existing `derive_index_name()` | Already tested, consistent |

**Key insight:** PostgreSQL's system catalogs (`information_schema`, `pg_table_size()`) provide reliable metadata without manual tracking. The MCP SDK handles all protocol complexity.

## Common Pitfalls

### Pitfall 1: stdout Corruption in MCP Server
**What goes wrong:** Server outputs debug messages to stdout, corrupting JSON-RPC messages.
**Why it happens:** Python's `print()` defaults to stdout; common habit from CLI development.
**How to avoid:**
- Configure logging to stderr: `logging.basicConfig(stream=sys.stderr)`
- Never use `print()` in MCP server code
- Use `ctx.info()`, `ctx.error()` from Context parameter for structured logging
**Warning signs:** MCP client reports "invalid JSON" or connection drops unexpectedly.

### Pitfall 2: Missing Index Error Handling
**What goes wrong:** Search or stats fails with cryptic SQL error when index doesn't exist.
**Why it happens:** Table name is constructed but table may not exist.
**How to avoid:**
- Check if table exists before querying
- Return user-friendly error: "Index 'foo' not found. Run 'cocosearch list' to see available indexes."
**Warning signs:** psycopg.errors.UndefinedTable exceptions.

### Pitfall 3: Clear Without Confirmation (CLI)
**What goes wrong:** User accidentally deletes important index.
**Why it happens:** No confirmation prompt by default.
**How to avoid:**
- Default to confirmation prompt: "Delete index 'myproject'? [y/N]"
- Require `--force` flag to skip confirmation
- Print what will be deleted before prompting
**Warning signs:** User complaints about data loss.

### Pitfall 4: Infrastructure Not Running
**What goes wrong:** Cryptic connection errors when Postgres or Ollama not running.
**Why it happens:** Connection pool creation fails with timeout.
**How to avoid:**
- Catch connection errors early
- Return actionable error: "Cannot connect to PostgreSQL. Is the Docker container running? Start with: docker start coco-postgres"
**Warning signs:** Long timeouts followed by unhelpful errors.

### Pitfall 5: MCP Tool Parameters Not Validated
**What goes wrong:** LLM passes invalid parameters, tool crashes.
**Why it happens:** Type hints aren't enforced without validation.
**How to avoid:**
- Use type hints (FastMCP validates automatically)
- Add `Field()` annotations for constraints
- Return structured error with `isError: true` for invalid inputs
**Warning signs:** Unhandled exceptions in tool execution.

## Code Examples

Verified patterns from official sources:

### MCP Server Main Entry Point
```python
# src/cocosearch/mcp/server.py
# Source: https://modelcontextprotocol.io/docs/develop/build-server

import sys
import logging
from mcp.server.fastmcp import FastMCP

# CRITICAL: Logging must go to stderr for stdio transport
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)

mcp = FastMCP("cocosearch")

# Tools defined with @mcp.tool() decorator...

def main():
    """Entry point for MCP server."""
    mcp.run(transport="stdio")
```

### CLI Confirmation Prompt Pattern
```python
# Source: Standard CLI patterns

def clear_command(args: argparse.Namespace) -> int:
    """Execute the clear command with confirmation."""
    index_name = args.index

    # Verify index exists
    try:
        stats = get_index_stats(index_name)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1

    # Show what will be deleted
    console.print(f"Index: {index_name}")
    console.print(f"  Files: {stats['file_count']}")
    console.print(f"  Chunks: {stats['chunk_count']}")
    console.print(f"  Size: {stats['storage_size_pretty']}")

    # Confirm unless --force
    if not args.force:
        response = input(f"\nDelete index '{index_name}'? [y/N] ")
        if response.lower() != 'y':
            console.print("Cancelled.")
            return 0

    # Perform deletion
    clear_index(index_name)
    console.print(f"[green]Index '{index_name}' deleted.[/green]")
    return 0
```

### PostgreSQL Table Discovery Query
```sql
-- Find all cocosearch index tables
-- Source: PostgreSQL information_schema documentation

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'codeindex_%__%_chunks'
ORDER BY table_name;

-- Get statistics for an index
SELECT
    COUNT(DISTINCT filename) as file_count,
    COUNT(*) as chunk_count,
    pg_table_size('codeindex_myproject__myproject_chunks') as storage_bytes
FROM codeindex_myproject__myproject_chunks;
```

### MCP Tool with Error Handling
```python
# Source: https://mcpcat.io/guides/error-handling-custom-mcp-servers/

from typing import Annotated
from pydantic import Field

@mcp.tool()
def clear_index(
    index_name: Annotated[str, Field(description="Name of the index to clear")]
) -> dict:
    """Clear (delete) a code index.

    WARNING: This permanently deletes all indexed data for this codebase.
    """
    try:
        # Verify index exists first
        stats = get_index_stats(index_name)

        # Perform deletion
        pool = get_connection_pool()
        table_name = get_table_name(index_name)

        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

        return {
            "success": True,
            "message": f"Index '{index_name}' deleted",
            "files_removed": stats['file_count'],
            "chunks_removed": stats['chunk_count'],
        }
    except ValueError as e:
        # Index doesn't exist - return error in result, not exception
        return {
            "success": False,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear index: {e}",
        }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON-RPC | FastMCP decorators | MCP SDK 1.0 | Simpler tool definition |
| sync-only tools | async/sync both supported | MCP SDK 1.2.0 | Better I/O handling |
| N/A | Structured output (outputSchema) | MCP spec 2025-06-18 | Type-safe returns |

**Deprecated/outdated:**
- `StdioServerTransport` class (use `transport="stdio"` parameter instead)
- Manual tool schema definition (use type hints, auto-generated by FastMCP)

## Open Questions

Things that couldn't be fully resolved:

1. **Staleness Detection Implementation**
   - What we know: CONTEXT.md mentions "X files modified since last index"
   - What's unclear: CocoIndex doesn't store "last indexed time" per file; would need to scan files and compare mtimes
   - Recommendation: Defer staleness to future enhancement; focus on core stats first

2. **CocoIndex Flow Cleanup**
   - What we know: Clearing the table removes data, but CocoIndex may have internal state
   - What's unclear: Whether CocoIndex tracks flows in a registry that needs cleanup
   - Recommendation: Use DROP TABLE for now; test if re-indexing works after clear

3. **MCP Progress Reporting for Index**
   - What we know: FastMCP supports `ctx.report_progress()`
   - What's unclear: How to integrate with existing Rich progress in indexer
   - Recommendation: Keep CLI and MCP progress separate; MCP uses Context, CLI uses Rich

## Sources

### Primary (HIGH confidence)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Server implementation, FastMCP usage
- [MCP Build Server Tutorial](https://modelcontextprotocol.io/docs/develop/build-server) - Complete Python example
- [FastMCP Tools Documentation](https://gofastmcp.com/servers/tools) - Tool decorator, Context, error handling
- [PostgreSQL Table Size Functions](https://neon.com/postgresql/postgresql-administration/postgresql-database-indexes-table-size) - pg_table_size(), pg_total_relation_size()

### Secondary (MEDIUM confidence)
- [Git rev-parse Documentation](https://git-scm.com/docs/git-rev-parse) - --show-toplevel for repo root
- [MCP Error Handling Best Practices](https://mcpcat.io/guides/error-handling-custom-mcp-servers/) - isError flag, error responses

### Tertiary (LOW confidence)
- CocoIndex flow naming: Derived from existing code patterns, not official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages already in use or installed
- Architecture patterns: HIGH - Based on official MCP SDK documentation and existing codebase structure
- Pitfalls: HIGH - From official MCP documentation on stdio transport and error handling
- Statistics queries: HIGH - Standard PostgreSQL system catalogs

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - MCP SDK stable, PostgreSQL metadata queries stable)
