# Phase 38: Multi-Repo MCP Support - Research

**Researched:** 2026-02-05
**Domain:** MCP server configuration, multi-repository support, cwd handling
**Confidence:** HIGH

## Summary

Research focused on enabling single-registration MCP usage across multiple repositories. The core challenge is that MCP servers run in isolated environments (uvx cache) with no automatic workspace context. Three key areas investigated: (1) passing workspace path to MCP server, (2) detecting project root from arbitrary cwd, (3) providing helpful error messaging when indexes don't exist.

**Key findings:**
- The `--directory $(pwd)` pattern is the recommended approach for passing workspace context to uvx-launched MCP servers
- Project detection infrastructure already exists via `find_project_root()` function (git root → config → None)
- Index staleness detection already implemented via metadata table `updated_at` timestamp
- Error messaging patterns established in MCP ecosystem emphasize friendly tone + actionable commands + common causes

**Primary recommendation:** Add `--project-from-cwd` flag to MCP server that reads cwd at runtime, validates with `find_project_root()`, and returns structured error responses for unindexed projects.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastMCP | 1.26.0+ | MCP server framework | Official Python SDK for MCP, already in use |
| psycopg[pool] | 3.3.2+ | Database connection pooling | Already used for PostgreSQL access |
| pathlib | stdlib | Path resolution | Python standard library, cross-platform |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| subprocess | stdlib | Git command execution | For git-based detection (already implemented) |
| datetime | stdlib | Timestamp comparison | For staleness detection (already implemented) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `--directory $(pwd)` | Environment variable `WORKSPACE_PATH` | Less explicit, requires client configuration |
| Metadata table | File mtime via os.stat | No cross-machine sync, loses update history |
| Git-based staleness | File mtime comparison | More accurate but requires filesystem access |

**Installation:**
No additional dependencies required - all functionality uses existing stack.

## Architecture Patterns

### Recommended Project Structure
```
src/cocosearch/
├── mcp/
│   └── server.py           # Add --project-from-cwd flag handling
├── management/
│   ├── context.py          # Existing: find_project_root, resolve_index_name
│   ├── metadata.py         # Existing: register_index_path, get_index_metadata
│   └── stats.py            # Existing: check_staleness function
```

### Pattern 1: Workspace Path Injection
**What:** Pass current working directory to MCP server via CLI argument
**When to use:** User-scoped MCP registration for multi-repo support
**Example:**
```bash
# Claude Code user-scope registration
claude mcp add --scope user cocosearch -- \
  uvx --from /path/to/cocosearch cocosearch mcp --project-from-cwd
```

**Why this works:**
- `os.getcwd()` in MCP server returns the workspace path, not uvx cache
- Documented pattern from MCP GitHub issues and similar servers
- Source: [How to access the current working directory when an MCP server is launched via uvx · Issue #1520](https://github.com/modelcontextprotocol/python-sdk/issues/1520)

### Pattern 2: Project Detection Priority Chain
**What:** Walk directory tree to find project boundaries
**When to use:** When user doesn't specify explicit index_name
**Example:**
```python
# From src/cocosearch/management/context.py (already implemented)
def find_project_root(start_path: Path | None = None) -> tuple[Path | None, str | None]:
    """Walk up directory tree to find project root.

    Priority:
    1. .git directory (git repository root)
    2. cocosearch.yaml (explicit project configuration)
    3. None (no project markers found)
    """
```

**Why this works:**
- Git root is universally recognized project boundary
- Config file allows explicit override for monorepos
- Matches user mental model of "project"

### Pattern 3: Structured Error Responses
**What:** Return error objects with actionable guidance, not exceptions
**When to use:** All error conditions in MCP tools
**Example:**
```python
# Unindexed project error (friendly + actionable)
return [{
    "error": "Index not found",
    "message": (
        f"Project detected at {root_path} but not indexed. "
        f"Index this project first using:\n"
        f"  CLI: cocosearch index {root_path}\n"
        f"  MCP: index_codebase(path='{root_path}')"
    ),
    "detected_path": str(root_path),
    "suggested_index_name": index_name,
    "results": []
}]
```

**Why this works:**
- LLMs can parse structured errors and suggest fixes to users
- Includes exact command to run (copy-paste ready)
- Distinguishes between error types (not found vs collision vs stale)
- Source: [Error Handling in MCP Servers - Best Practices Guide](https://mcpcat.io/guides/error-handling-custom-mcp-servers/)

### Anti-Patterns to Avoid
- **Silent fallback to cwd**: Don't silently use cwd if git root not found - this breaks multi-repo use case
- **Raising Python exceptions in MCP tools**: Return structured error dicts instead, LLMs can't catch exceptions
- **Vague error messages**: "Index not found" without path or fix is confusing to LLMs
- **Blocking prompts in MCP tools**: Return guidance messages instead, let user decide when to act

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path canonicalization | Manual os.path normalization | `Path.resolve()` | Handles symlinks, relative paths, platform differences |
| Git root detection | Parse .git/config | `git rev-parse --show-toplevel` | Handles submodules, worktrees, edge cases |
| Staleness threshold | Hard-coded "7 days" | Configurable via CLI flag | Different teams have different cadences |
| Timestamp timezone handling | Manual UTC conversion | PostgreSQL TIMESTAMP WITH TIME ZONE | Database handles timezone correctly |

**Key insight:** The Python standard library and PostgreSQL provide robust primitives for path/time operations. Custom implementations introduce bugs (symlink loops, timezone errors, platform quirks).

## Common Pitfalls

### Pitfall 1: uvx cwd Behavior
**What goes wrong:** Assuming `os.getcwd()` returns workspace path when MCP server launched via uvx
**Why it happens:** uvx runs in isolated cache environment (`~/.cache/uv/...`), not workspace
**How to avoid:** Document `--directory $(pwd)` pattern in MCP registration examples
**Warning signs:** MCP tools can't find user's files, path operations fail

**Verified solution:** From [mcp-server-git Issue #3029](https://github.com/modelcontextprotocol/servers/issues/3029):
> "The `--directory` flag ensures uvx passes the workspace path, not the cache path."

### Pitfall 2: Index Name Collision
**What goes wrong:** Two projects with same directory name (e.g., "frontend") map to same index
**Why it happens:** `derive_index_name()` uses basename only, ignores full path
**How to avoid:**
- Store canonical path in metadata table (already implemented)
- Check for collision on `register_index_path()` (already implemented)
- Return clear error explaining mismatch + resolution steps
**Warning signs:** Search returns wrong project's code, metadata shows different path

**Existing code handles this:**
```python
# From src/cocosearch/management/metadata.py
if existing and existing["canonical_path"] != canonical:
    raise ValueError(
        f"Index name collision detected: '{index_name}'\n"
        f"  Existing path: {existing['canonical_path']}\n"
        f"  New path: {canonical}\n\n"
        f"To resolve:\n"
        f"  1. Set explicit indexName in cocosearch.yaml, or\n"
        f"  2. Use --index-name flag"
    )
```

### Pitfall 3: Stale Index False Positives
**What goes wrong:** Recently updated indexes flagged as stale
**Why it happens:** Naive timestamp comparison without timezone normalization
**How to avoid:**
- Use `datetime.now(timezone.utc)` for current time
- Ensure metadata table `updated_at` uses TIMESTAMP WITH TIME ZONE
- Handle naive timestamps by assuming UTC
**Warning signs:** Staleness warnings immediately after successful indexing

**Existing implementation is correct:**
```python
# From src/cocosearch/management/stats.py
now = datetime.now(timezone.utc)
if updated_at.tzinfo is None:
    updated_at = updated_at.replace(tzinfo=timezone.utc)
delta = now - updated_at
days_since_update = delta.days
```

### Pitfall 4: Missing Error Context
**What goes wrong:** LLM can't help user because error lacks actionable information
**Why it happens:** Returning generic error messages without paths, commands, or causes
**How to avoid:**
- Include detected paths in error response
- Provide exact command to fix issue
- List common causes beyond immediate fix
- Use consistent error structure across all MCP tools
**Warning signs:** Users paste errors into chat asking "what does this mean?"

**Example from CONTEXT.md:**
```
Error: "No index found for this project. Run: `coco index /path/to/project`. Common causes: new project, moved directory, cleared cache."
```

## Code Examples

Verified patterns from official sources:

### MCP Server CLI Flag Handling
```python
# Add to src/cocosearch/cli.py mcp_command()
def mcp_command(args: argparse.Namespace) -> int:
    """Start the MCP server."""
    from cocosearch.mcp import run_server

    # Get project path from --project-from-cwd or use None
    project_path = None
    if args.project_from_cwd:
        project_path = os.getcwd()

    # Pass to server via environment or global variable
    if project_path:
        os.environ["COCOSEARCH_PROJECT_PATH"] = project_path

    run_server(transport=args.transport, host="0.0.0.0", port=args.port)
```

### Auto-Detect with Error Handling
```python
# Pattern for search_code tool in src/cocosearch/mcp/server.py
def search_code(query: str, index_name: str | None = None, ...) -> list[dict]:
    """Search indexed code using natural language."""

    if index_name is None:
        # Auto-detect from cwd (passed via --project-from-cwd)
        root_path, detection_method = find_project_root()

        if root_path is None:
            # Not in a project directory
            return [{
                "error": "No project detected",
                "message": (
                    "Not in a git repository or directory with cocosearch.yaml. "
                    "Either navigate to your project directory, or specify "
                    "index_name parameter explicitly."
                ),
                "results": []
            }]

        # Resolve index name using priority chain
        index_name = resolve_index_name(root_path, detection_method)

        # Check if index exists
        indexes = mgmt_list_indexes()
        index_names = {idx["name"] for idx in indexes}

        if index_name not in index_names:
            # Project detected but not indexed
            return [{
                "error": "Index not found",
                "message": (
                    f"Project detected at {root_path} but not indexed. "
                    f"Index this project first using:\n"
                    f"  CLI: cocosearch index {root_path}\n"
                    f"  MCP: index_codebase(path='{root_path}')"
                ),
                "detected_path": str(root_path),
                "suggested_index_name": index_name,
                "results": []
            }]

        # Continue with search...
```

### Staleness Warning (Footer Pattern)
```python
# Pattern for adding staleness warnings to search results
def search_code(...) -> list[dict]:
    # ... execute search ...

    # Check staleness and add footer warning if needed
    is_stale, days_since_update = check_staleness(index_name, threshold_days=7)

    if is_stale and days_since_update > 0:
        # Add warning as last result (footer pattern)
        results.append({
            "warning": "Index may be stale",
            "message": (
                f"Index last updated {days_since_update} days ago. "
                f"Run `cocosearch index {root_path}` to refresh."
            ),
            "staleness_days": days_since_update
        })

    return results
```

### User-Scope MCP Registration
```bash
# Claude Code user-scope registration (stdio transport)
# Source: https://code.claude.com/docs/en/mcp

claude mcp add --scope user cocosearch -- \
  uvx --from /absolute/path/to/cocosearch cocosearch mcp --project-from-cwd

# Verify registration
claude mcp list
```

```json
// Claude Desktop user-scope registration (HTTP transport via mcp-remote)
// Config location: ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "cocosearch": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:3000/mcp"]
    }
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Project-scope only | User-scope registration | MCP 1.0 (2025) | Register once, use everywhere |
| Hard-coded paths | `--directory $(pwd)` pattern | MCP Python SDK 1.5+ | Workspace context in uvx |
| Silent failures | Structured error responses | MCP best practices (2026) | LLMs can guide users to fixes |
| File mtime staleness | Metadata table timestamps | CocoSearch v1.8 | Cross-machine consistency |

**Deprecated/outdated:**
- **Project-scoped MCP servers**: Claude Code 1.0.18+ supports `--scope user` for global registration
- **Environment variable for workspace**: `--directory $(pwd)` is clearer and more explicit than `WORKSPACE_PATH` env var
- **Exception-based MCP errors**: Return structured dicts instead of raising exceptions (LLMs can't catch them)

## Open Questions

Things that couldn't be fully resolved:

1. **Should `--project-from-cwd` be the default for MCP mode?**
   - What we know: User-scope registration is the recommended pattern for multi-repo support
   - What's unclear: Whether project-scope registration still has valid use cases (CI/CD, Docker?)
   - Recommendation: Make `--project-from-cwd` optional flag, document user-scope as recommended approach

2. **How to handle monorepos with multiple cocosearch.yaml files?**
   - What we know: Current implementation treats top-level git root as project boundary
   - What's unclear: Whether subprojects in monorepos should be separately indexable
   - Recommendation: Defer to v2.0 - monorepo support is out of scope for v1.9

3. **Should staleness warnings appear in search results or as separate field?**
   - What we know: Footer pattern (last result) is common in search UIs
   - What's unclear: Whether LLMs prefer dedicated `warnings` field or inline messages
   - Recommendation: Add as footer note (inline with results) per CONTEXT.md decision

## Sources

### Primary (HIGH confidence)
- [MCP Python SDK Issue #1520 - uvx cwd behavior](https://github.com/modelcontextprotocol/python-sdk/issues/1520) - Verified uvx `--directory` pattern
- [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp) - Official `--scope user` documentation
- [Error Handling in MCP Servers Best Practices](https://mcpcat.io/guides/error-handling-custom-mcp-servers/) - Structured error patterns
- Existing codebase: `src/cocosearch/management/context.py`, `metadata.py`, `stats.py` - Verified implementations

### Secondary (MEDIUM confidence)
- [mcp-server-git Issue #3029 - Git root auto-detection](https://github.com/modelcontextprotocol/servers/issues/3029) - Community pattern for project detection
- [Code Index MCP Server by John Huang](https://github.com/johnhuang316/code-index-mcp) - Similar implementation using `--project-path` flag

### Tertiary (LOW confidence)
- [LLMEO Strategies 2026 - Index freshness](https://techiehub.blog/llmeo-strategies-2026/) - General staleness patterns (not code-search specific)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, no new dependencies
- Architecture: HIGH - Patterns verified in existing codebase and MCP ecosystem
- Pitfalls: HIGH - Identified from actual GitHub issues and implementation edge cases

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - MCP ecosystem stable, patterns unlikely to change)
