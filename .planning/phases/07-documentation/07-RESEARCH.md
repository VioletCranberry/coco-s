# Phase 7: Documentation - Research

**Researched:** 2026-01-26
**Domain:** Technical documentation, MCP client configuration, CLI reference
**Confidence:** HIGH

## Summary

Phase 7 involves creating comprehensive user documentation for CocoSearch in a single README.md file. The documentation must cover three main areas: (1) installation prerequisites (Ollama, PostgreSQL with pgvector, Python/UV), (2) MCP server configuration for three clients (Claude Code, Claude Desktop, OpenCode), and (3) CLI command reference with examples.

The key insight is that all three MCP clients use similar JSON configuration patterns but with different file locations and slight syntax variations. Claude Code additionally supports CLI-based server management. GitHub natively renders Mermaid diagrams, making them ideal for architecture visuals without external image hosting.

**Primary recommendation:** Structure the README with a quick start section first, followed by detailed installation, then MCP configuration sections for each client, and finally CLI reference organized by workflow.

## Standard Stack

The established tools for this documentation:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Markdown | GitHub Flavored | Documentation format | Native GitHub rendering, version control friendly |
| Mermaid | Native to GitHub | Architecture diagrams | Text-based, renders in GitHub without external hosting |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| Code blocks with syntax highlighting | Configuration examples | JSON/YAML/bash config snippets |
| Collapsible sections (`<details>`) | Optional/advanced content | Platform-specific troubleshooting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Mermaid | Static PNG images | PNG requires hosting, doesn't scale, harder to maintain |
| Single README | docs/ folder | User decided single file; simpler, GitHub-native |

## Architecture Patterns

### Recommended README Structure
```
README.md
├── Title + badges (optional)
├── One-line description
├── Table of Contents (auto-generated from headers)
├── What CocoSearch Does (pitch)
├── Architecture Diagram (Mermaid)
├── Quick Start
│   ├── CLI Demo (index → search)
│   └── MCP Setup Path
├── Installation
│   ├── Prerequisites
│   ├── Ollama Setup
│   ├── PostgreSQL Setup (Docker)
│   └── CocoSearch Installation
├── MCP Configuration
│   ├── Claude Code
│   ├── Claude Desktop
│   └── OpenCode
├── CLI Reference
│   ├── Indexing Commands
│   ├── Search Commands
│   └── Management Commands
├── Configuration (.cocosearch.yaml)
└── Environment Variables
```

### Pattern 1: Context-First Documentation
**What:** Start with "what and why" before "how"
**When to use:** User documentation where motivation matters
**Example:**
```markdown
# CocoSearch

Local-first semantic code search via MCP. Search your codebase using natural language, entirely offline.

## What CocoSearch Does

CocoSearch indexes your code and enables semantic search powered by local embeddings.
All processing happens on your machine - no data leaves your system.

- **Index codebases** using Ollama embeddings stored in PostgreSQL with pgvector
- **Search semantically** via CLI or any MCP-compatible client (Claude Code, Claude Desktop, OpenCode)
- **Stay private** - everything runs locally
```

### Pattern 2: Copy-Paste Ready Config Blocks
**What:** Complete, tested configuration snippets users can copy directly
**When to use:** All configuration examples
**Example:**
```markdown
Add to `~/.claude.json`:

\`\`\`json
{
  "mcpServers": {
    "cocosearch": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/cocosearch", "cocosearch", "mcp"],
      "env": {
        "COCOINDEX_DATABASE_URL": "postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
      }
    }
  }
}
\`\`\`
```

### Pattern 3: Expected Output Display
**What:** Show what user will see after running a command
**When to use:** CLI documentation for verification
**Example:**
```markdown
\`\`\`bash
cocosearch index ./my-project
\`\`\`

Output:
\`\`\`
Using derived index name: my_project
Indexing ./my-project...
✓ Indexed 42 files (127 chunks)
\`\`\`
```

### Anti-Patterns to Avoid
- **Jargon without explanation:** Don't say "pgvector" without explaining it's a PostgreSQL extension for vector similarity
- **Assuming environment:** Specify exact paths, don't use `~` in JSON (expand to full path)
- **Missing verification steps:** Always show how to verify each setup step worked

## Don't Hand-Roll

Problems with existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diagrams | External PNG images | Mermaid in markdown | Renders natively on GitHub, easy to update |
| Table of Contents | Manual links | Markdown headers (GitHub auto-generates) | GitHub adds ToC via outline panel |
| Config validation | Instructions to "check if it works" | Specific verification commands | Users need concrete success criteria |

**Key insight:** GitHub Markdown has powerful native features (Mermaid rendering, auto ToC, syntax highlighting). Use these instead of external tools or manual solutions.

## Common Pitfalls

### Pitfall 1: Path Expansion in JSON
**What goes wrong:** JSON doesn't expand `~` - users copy config with `~/path` and it fails silently
**Why it happens:** Shell expands `~` but JSON parsers don't
**How to avoid:** Always use absolute paths in JSON examples, add note about path expansion
**Warning signs:** MCP server shows "failed" status, "file not found" errors

### Pitfall 2: Environment Variable Visibility
**What goes wrong:** MCP servers can't find COCOINDEX_DATABASE_URL
**Why it happens:** Environment variables from shell profile aren't inherited by GUI apps
**How to avoid:** Show `env` block in MCP config JSON explicitly
**Warning signs:** "database connection failed" in MCP server logs

### Pitfall 3: Docker vs Native PostgreSQL
**What goes wrong:** Users with native PostgreSQL can't use Docker Compose
**Why it happens:** Port 5432 conflict
**How to avoid:** Show both Docker and native pgvector installation options (per CONTEXT.md)
**Warning signs:** "port already in use" error

### Pitfall 4: Claude Desktop Config Location
**What goes wrong:** Config file in wrong location, MCP server not discovered
**Why it happens:** Location varies by OS
**How to avoid:** Show exact paths for macOS, Linux, and Windows
**Warning signs:** Server not appearing in Claude Desktop, no hammer icon

### Pitfall 5: OpenCode Config vs Claude Config Differences
**What goes wrong:** Users copy Claude config structure to OpenCode
**Why it happens:** Similar but not identical JSON structure
**How to avoid:** Show complete examples for each client, highlight differences
**Warning signs:** OpenCode ignores the MCP server

## Code Examples

### Mermaid Architecture Diagram
```mermaid
flowchart LR
    subgraph Local
        Code[Codebase] --> Indexer
        Indexer --> |embeddings| PG[(PostgreSQL + pgvector)]
        Ollama[Ollama] --> |nomic-embed-text| Indexer
    end

    subgraph Clients
        CLI[CLI] --> Search
        Claude[Claude Code/Desktop] --> |MCP| Search
        OpenCode --> |MCP| Search
    end

    Search --> PG
    Ollama --> Search
```

### Claude Code MCP Configuration
Source: https://code.claude.com/docs/en/mcp
```bash
# Add CocoSearch MCP server
claude mcp add --transport stdio --scope user \
  --env COCOINDEX_DATABASE_URL=postgresql://cocoindex:cocoindex@localhost:5432/cocoindex \
  cocosearch -- uv run --directory /absolute/path/to/cocosearch cocosearch mcp

# Verify it was added
claude mcp list

# Check status inside Claude Code
/mcp
```

Or add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/cocosearch", "cocosearch", "mcp"],
      "env": {
        "COCOINDEX_DATABASE_URL": "postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
      }
    }
  }
}
```

### Claude Desktop MCP Configuration
Source: https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop

Config file locations:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/cocosearch", "cocosearch", "mcp"],
      "env": {
        "COCOINDEX_DATABASE_URL": "postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
      }
    }
  }
}
```

Verification:
1. Restart Claude Desktop
2. Look for hammer icon in chat interface
3. Click hammer to see "cocosearch" tools listed

### OpenCode MCP Configuration
Source: https://opencode.ai/docs/mcp-servers/

Config file locations:
- **Global:** `~/.config/opencode/opencode.json`
- **Project:** `opencode.json` in project root

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "cocosearch": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/absolute/path/to/cocosearch", "cocosearch", "mcp"],
      "enabled": true,
      "environment": {
        "COCOINDEX_DATABASE_URL": "postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
      }
    }
  }
}
```

Key differences from Claude configs:
- Uses `"type": "local"` instead of implicit stdio
- `command` is an array, not a string
- Uses `"environment"` instead of `"env"`
- Has explicit `"enabled": true` field

### CLI Command Reference Pattern
```markdown
### `cocosearch index`

Index a codebase for semantic search.

**Synopsis:**
\`\`\`bash
cocosearch index <path> [options]
\`\`\`

**Options:**
| Flag | Description | Default |
|------|-------------|---------|
| `-n, --name` | Index name | Derived from directory |
| `-i, --include` | Additional include patterns | (none) |
| `-e, --exclude` | Additional exclude patterns | (none) |
| `--no-gitignore` | Ignore .gitignore | Respects .gitignore |

**Example:**
\`\`\`bash
cocosearch index ./my-project --name myproject
\`\`\`

Output:
\`\`\`
Using derived index name: myproject
Indexing ./my-project...
✓ Indexed 42 files (127 chunks)
\`\`\`
```

### Installation Commands
```bash
# 1. Install Ollama
brew install ollama
ollama serve  # In separate terminal, or runs as service
ollama pull nomic-embed-text

# 2. Start PostgreSQL with pgvector
docker compose up -d

# 3. Install CocoSearch
uv sync
uv run cocosearch --help
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE transport for MCP | HTTP transport preferred | 2025 | SSE deprecated, use HTTP where available |
| Manual JSON config only | CLI commands + JSON config | 2025 | Claude Code CLI simplifies setup |
| Static diagram images | Mermaid in markdown | 2022 | GitHub native rendering, easier maintenance |

**Deprecated/outdated:**
- SSE transport: Use HTTP for remote servers, stdio for local servers
- `--scope global`: Now called `--scope user` in Claude Code
- `--scope project`: Now called `--scope local` in Claude Code (confusing, but current)

## Open Questions

Things that couldn't be fully resolved:

1. **Windows-specific MCP commands**
   - What we know: Windows requires `cmd /c` wrapper for npx commands
   - What's unclear: Whether UV-based commands also need wrapper
   - Recommendation: Test on Windows or note potential issue with "Windows users may need cmd /c wrapper"

2. **Ollama service management**
   - What we know: `ollama serve` runs the server
   - What's unclear: Whether brew installs a launchd service automatically on macOS
   - Recommendation: Show manual `ollama serve` approach, note brew may configure auto-start

## Sources

### Primary (HIGH confidence)
- Claude Code MCP documentation: https://code.claude.com/docs/en/mcp
- OpenCode MCP documentation: https://opencode.ai/docs/mcp-servers/
- Claude Desktop local MCP: https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop

### Secondary (MEDIUM confidence)
- GitHub Mermaid support: https://github.blog/developer-skills/github/include-diagrams-markdown-files-mermaid/
- README best practices: https://www.freecodecamp.org/news/how-to-write-a-good-readme-file/

### Tertiary (LOW confidence)
- WebSearch results for general documentation practices

## Metadata

**Confidence breakdown:**
- MCP configurations: HIGH - Official documentation verified
- CLI reference: HIGH - Derived from actual source code analysis
- Installation steps: MEDIUM - Standard tools, may vary by platform
- Diagrams/structure: HIGH - GitHub native features well documented

**Research date:** 2026-01-26
**Valid until:** 60+ days (documentation patterns stable, MCP configs may change with client updates)
