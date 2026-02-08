## CLI Reference

CocoSearch provides a command-line interface for indexing and searching code. Output is JSON by default (for scripting/MCP); use `--pretty` for human-readable output.

### Indexing Commands

`cocosearch index <path> [options]`

Index a codebase for semantic search.

| Flag             | Description                        | Default                |
| ---------------- | ---------------------------------- | ---------------------- |
| `-n, --name`     | Index name                         | Derived from directory |
| `-i, --include`  | Include file patterns (repeatable) | See defaults below     |
| `-e, --exclude`  | Exclude file patterns (repeatable) | None                   |
| `--no-gitignore` | Ignore .gitignore patterns         | Respects .gitignore    |

**Example:**

```bash
cocosearch index ./my-project --name myproject
```

Output:

```
Using derived index name: myproject
Indexing ./my-project...
Indexed 42 files
```

### Searching Commands

`cocosearch search <query> [options]`
`cocosearch search --interactive`

Search indexed code using natural language.

| Flag                   | Description                        | Default              |
| ---------------------- | ---------------------------------- | -------------------- |
| `-n, --index`          | Index to search                    | Auto-detect from cwd |
| `-l, --limit`          | Max results                        | 10                   |
| `--lang`               | Filter by language                 | None                 |
| `--min-score`          | Minimum similarity (0-1)           | 0.3                  |
| `-A, --after-context`  | Lines to show after match          | Smart expand         |
| `-B, --before-context` | Lines to show before match         | Smart expand         |
| `-C, --context`        | Lines before and after             | Smart expand         |
| `--no-smart`           | Disable smart context expansion    | Off                  |
| `--hybrid`             | Force hybrid search                | Auto-detect          |
| `--symbol-type`        | Filter by symbol type (repeatable) | None                 |
| `--symbol-name`        | Filter by symbol name pattern      | None                 |
| `--no-cache`           | Bypass query cache (for debugging) | Off                  |
| `-i, --interactive`    | Enter REPL mode                    | Off                  |
| `--pretty`             | Human-readable output              | JSON                 |

**Examples:**

```bash
# Basic search
cocosearch search "authentication logic" --pretty

# Filter by language
cocosearch search "error handling" --lang python

# Inline language filter
cocosearch search "database connection lang:go"

# Interactive mode
cocosearch search --interactive
```

Output (--pretty):

```
[1] src/auth/login.py:45-67 (score: 0.89)
    def authenticate_user(username: str, password: str) -> User:
        """Authenticate user credentials against database."""
        ...
```

### Managing Indexes

**List indexes:** `cocosearch list [--pretty]`

Show all available indexes.

```bash
cocosearch list --pretty
```

Output:

```
       Indexes
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Table                  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ myproject  │ cocosearch_myproject   │
│ another    │ cocosearch_another     │
└────────────┴────────────────────────┘
```

**Index statistics:** `cocosearch stats [index] [--pretty]`

Show statistics for one or all indexes.

```bash
cocosearch stats myproject --pretty
```

Output:

```
    Index: myproject
┏━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric  ┃ Value     ┃
┡━━━━━━━━━╇━━━━━━━━━━━┩
│ Files   │ 42        │
│ Chunks  │ 127       │
│ Size    │ 2.3 MB    │
└─────────┴───────────┘
```

**Clear index:** `cocosearch clear <index> [--force] [--pretty]`

Delete an index and all its data. Prompts for confirmation unless `--force`.

```bash
cocosearch clear myproject --force
```

Output:

```
Index 'myproject' deleted successfully
```

**List supported languages:** `cocosearch languages [--json]`

Show all languages CocoSearch can index with extensions and symbol support.

```bash
cocosearch languages
```

**Start MCP server:** `cocosearch mcp`

Start the MCP server for LLM integration. Typically invoked by MCP clients, not directly.

```bash
cocosearch mcp  # Runs until killed, used by Claude/OpenCode
```

## Observability

Monitor index health, language distribution, and symbol breakdown.

### Index Statistics

```bash
cocosearch stats myproject --pretty
```

Output shows file count, chunk count, size, and staleness warnings:

```
    Index: myproject
┏━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric  ┃ Value       ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Files   │ 68          │
│ Chunks  │ 488         │
│ Size    │ 2.1 MB      │
│ Updated │ 2 days ago  │
└─────────┴─────────────┘
```

### Language Breakdown

View per-language file counts, chunk distribution, and line counts:

```bash
cocosearch stats myproject --pretty
```

```
           Language Statistics
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Language   ┃ Files ┃ Chunks ┃  Lines ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ python     │    42 │    287 │  3,521 │
│ typescript │    18 │    156 │  2,103 │
│ markdown   │     5 │     32 │    654 │
├────────────┼───────┼────────┼────────┤
│ TOTAL      │    68 │    488 │  6,516 │
└────────────┴───────┴────────┴────────┘
```

### Dashboard

Web-based stats visualization:

```bash
cocosearch serve-dashboard
# Opens browser to http://localhost:8080
```

The dashboard displays real-time index health with language distribution charts.

### JSON Output

Machine-readable stats for automation:

```bash
cocosearch stats myproject --json
```
