---
name: cocosearch-opencode
description: Semantic code search via MCP for OpenCode. Use for understanding unfamiliar code, finding related functionality, or exploring symbol hierarchies.
---

# CocoSearch for OpenCode

Semantic code search with symbol awareness via MCP protocol.

## Quick Setup

**1. Install UV:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
```

**2. Install CocoSearch:**
```bash
uv pip install cocosearch
```

**3. Verify installation:**
```bash
cocosearch --version
```

**4. Configure MCP (see next section)**

**5. Verify connection:**
```bash
cocosearch stats  # Should connect to database
```

## MCP Configuration

**Config file locations:**
- Global: `~/.config/opencode/opencode.json`
- Project: `opencode.json` in project root

**Config content:**
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "cocosearch": {
      "type": "local",
      "command": [
        "uv",
        "run",
        "--directory",
        "/absolute/path/to/cocosearch",
        "cocosearch",
        "mcp"
      ],
      "enabled": true,
      "environment": {
        "COCOSEARCH_DATABASE_URL": "postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
      }
    }
  }
}
```

**Key differences from Claude Code:**
- Uses `"type": "local"` (explicit, not implicit)
- `command` is an array (not separate command/args)
- Uses `"environment"` (not `"env"`)
- Requires `"enabled": true`

**After config:**
1. Restart OpenCode
2. Check MCP status in OpenCode settings
3. Verify cocosearch tools available

## When to Use CocoSearch

**Use CocoSearch for:**
- Intent-based discovery: "find authentication logic"
  → Returns validateUser, checkCredentials even without keyword match
- Symbol exploration: "database handlers" --symbol-type function
  → Filters to functions with semantic understanding
- Cross-file patterns: "error handling patterns"
  → Finds conceptually similar code across files
- Context expansion: --smart shows full function/class automatically

**Use grep/ripgrep for:**
- Exact identifiers: `rg "getUserById"`
  → Faster for literal string lookup
- Regex patterns: `rg "TODO:.*urgent"`
  → Pattern matching CocoSearch doesn't support
- Known locations: `rg "import React" src/components/`
  → When you know exact text and location

**Use IDE tools for:**
- Go-to-definition (Cmd+Click / F12)
- Find-references (all usages of identifier)
- Rename refactoring (safe identifier changes)

## Workflow Examples

**1. Semantic discovery:**
```bash
cocosearch search "database connection handling"
```
Expected output:
```
[1] src/db/connect.py:45-67 (score: 0.89)
    def establish_connection(config: dict) -> Connection:
        """Create database connection with retry logic."""
        [... full function body ...]

[2] src/db/pool.py:30-45 (score: 0.82)
    class ConnectionPool:
        """Manages database connection pool."""
        [...]
```

**2. Hybrid search + symbol filter (power combo):**
```bash
cocosearch search "authenticate" --hybrid --symbol-type function
```
Expected output:
```
[1] src/auth/validate.py:22-38 (score: 0.93)
    def authenticate_user(username: str, password: str) -> User:
        """Validate user credentials."""
        [... implementation ...]

[2] src/api/middleware.py:15-28 (score: 0.87)
    def check_authentication(request: Request) -> bool:
        [...]
```

**3. Context expansion with smart mode:**
```bash
cocosearch search "error handler" --smart
```
Shows full enclosing function/class (up to 50 lines automatically).

**4. Language-specific search:**
```bash
cocosearch search "API routes" --lang typescript
```
Filters to TypeScript files only, semantic understanding of "routes" concept.

**5. Symbol name pattern:**
```bash
cocosearch search "User" --symbol-name "User*" --symbol-type class
```
Expected output:
```
[1] src/models/user.py:10-45 (score: 0.91)
    class User:
        """Core user model."""
        [... class definition ...]

[2] src/models/user.py:48-62 (score: 0.88)
    class UserProfile:
        """Extended user profile."""
        [...]
```

**6. Fixed context window:**
```bash
cocosearch search "validation" -C 10 --no-smart
```
Shows exactly 10 lines before/after each match (vs smart expansion).

## Anti-Patterns

**Don't use CocoSearch for:**
- Exact string matches → Use `rg "exact_string"`
- Regex patterns → Use `rg "pattern.*regex"`
- Single-file edits → Use IDE find/replace
- Rename refactoring → Use IDE rename tool

**Don't forget:**
- Reindex after major code changes: `cocosearch index . --name <index>`
- Symbol features require v1.7+ (reindex if upgrading)
- Check index health: `cocosearch stats <index>`

## Troubleshooting

For database setup, Docker installation, MCP debugging, and advanced configuration, see the [project README.md](https://github.com/fyodorovandrei/cocosearch#readme).

**Quick checks:**
- `cocosearch --version` → Shows version
- `cocosearch stats` → Connects to database
- Check OpenCode MCP status in settings
