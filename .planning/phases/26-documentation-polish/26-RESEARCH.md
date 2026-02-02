# Phase 26: Documentation & Polish - Research

**Researched:** 2026-02-02
**Domain:** Technical documentation for Docker deployment and MCP client configuration
**Confidence:** HIGH

## Summary

Phase 26 focuses on creating user documentation for the CocoSearch Docker deployment and MCP client integration. The research domain is documentation patterns rather than code implementation. The existing codebase already has a comprehensive README.md (614 lines) covering non-Docker installation and MCP configuration.

The documentation work involves:
1. Adding Docker quick start sections showing `docker run` commands
2. Providing copy-paste-ready MCP configuration for Claude Code and Claude Desktop
3. Documenting volume mounts for data persistence
4. Creating a component-based troubleshooting guide

Key finding: Claude Desktop cannot directly connect to HTTP/SSE remote servers via JSON config. Remote MCP servers require going through Settings > Connectors UI, OR using a proxy tool like `mcp-remote` or `mcp-proxy`. This is a critical detail for documentation accuracy.

**Primary recommendation:** Create two distinct quick start paths - one for Claude Code (direct stdio, no Docker networking needed) and one for Claude Desktop (requires mcp-remote proxy to bridge HTTP transport to stdio).

## Standard Stack

This phase is documentation-only. No new libraries or tools are being implemented.

### Documentation Tools/Patterns Used
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| Markdown | README format | Universal GitHub standard |
| Inline code comments | Docker command explanation | Improves copy-paste experience |
| JSON code blocks | MCP configuration examples | Native config format |
| Collapsible sections (optional) | Advanced topics | Reduces visual noise |

### MCP Proxy Tools (For Documentation Reference)
| Tool | Version | Purpose | When Documented |
|------|---------|---------|-----------------|
| mcp-remote | latest | Bridges HTTP/SSE to stdio for Claude Desktop | Claude Desktop HTTP setup |
| mcp-proxy | latest | Alternative stdio-to-HTTP bridge | Optional mention |

## Architecture Patterns

### Recommended Documentation Structure

Based on CONTEXT.md decisions, all documentation goes in README.md:

```
README.md
  |-- [Existing content]
  |
  |-- ## Docker Quick Start (NEW)
  |     |-- ### Claude Code Quick Start
  |     |-- ### Claude Desktop Quick Start
  |     |-- ### Data Persistence
  |
  |-- ## Troubleshooting Docker (NEW)
        |-- ### PostgreSQL Issues
        |-- ### Ollama Issues
        |-- ### MCP Server Issues
```

### Pattern 1: Transport-Specific Quick Starts

**What:** Separate quick start sections for each MCP client because they require different transports
**When to use:** When deployment differs by client type

**Claude Code uses stdio transport:**
- Simpler setup (direct container execution)
- No network port mapping needed for MCP
- Container runs interactively

**Claude Desktop uses HTTP transport (via proxy):**
- Requires port mapping (`-p 3000:3000`)
- Requires mcp-remote or similar proxy in config
- Container runs as daemon

### Pattern 2: Copy-Paste Ready Examples

**What:** Examples that work immediately without substitution
**When to use:** Quick start sections

Example approach:
```bash
# Works as-is - uses named volume for persistence
docker run -d \
  -v cocosearch-data:/data \
  -v "$PWD":/mnt/repos:ro \
  -p 3000:3000 \
  cocosearch
```

NOT:
```bash
# Requires user to replace placeholders
docker run -v /YOUR/CODE/PATH:/mnt/repos ...  # BAD
```

### Pattern 3: Component-First Troubleshooting

**What:** Organize troubleshooting by component (PostgreSQL, Ollama, MCP) not by symptom
**When to use:** Troubleshooting sections

Structure:
```
### PostgreSQL Issues
- Startup failures
- Connection refused

### Ollama Issues
- Model not found
- Embedding failures

### MCP Server Issues
- Health check failures
- Transport errors
```

### Anti-Patterns to Avoid

- **Placeholder values requiring substitution:** Use `$PWD` or `./.cocosearch-data` instead of `/path/to/your/code`
- **Mixing quick start with advanced options:** Keep quick start minimal, use separate sections for customization
- **Assuming Claude Desktop HTTP works directly:** Must document mcp-remote requirement
- **Documenting client-side MCP issues:** Link to official MCP docs instead

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Claude Desktop HTTP connection | Custom proxy documentation | mcp-remote package | Official Anthropic recommendation |
| Volume path portability | Complex path instructions | `$PWD` and named volumes | Works across shells |
| Environment variable docs | Custom format | Existing env var table in README | Consistency |

**Key insight:** The documentation challenge is not explaining Docker itself (audience knows Docker), but showing the specific CocoSearch configuration patterns that work.

## Common Pitfalls

### Pitfall 1: Claude Desktop HTTP Misconception
**What goes wrong:** Users try to add HTTP/SSE server directly to claude_desktop_config.json
**Why it happens:** Other MCP docs show direct JSON config
**How to avoid:** Explicitly document that Claude Desktop requires mcp-remote proxy for HTTP servers
**Warning signs:** User reports "connection refused" with correct URL

### Pitfall 2: Read-Only Volume Mount Confusion
**What goes wrong:** Users mount /mnt/repos without `:ro` flag, worry about modifications
**Why it happens:** Unclear what container does with mounted code
**How to avoid:** Always show `:ro` flag, explain it's for indexing (read-only operation)
**Warning signs:** Users asking if Docker will modify their code

### Pitfall 3: Data Loss on Container Removal
**What goes wrong:** Users run without `-v cocosearch-data:/data`, lose index on container stop
**Why it happens:** Quick start might skip persistence for brevity
**How to avoid:** Include volume mount in ALL examples, not just "advanced" section
**Warning signs:** Users reporting "index disappeared"

### Pitfall 4: Port Conflict on 3000
**What goes wrong:** Container fails to start because port 3000 is in use
**Why it happens:** Common development port (React, etc.)
**How to avoid:** Show `-p 3001:3000` alternative, mention port conflict in troubleshooting
**Warning signs:** "Port already in use" errors

### Pitfall 5: stdio vs HTTP Transport Confusion
**What goes wrong:** Users use HTTP config for Claude Code or vice versa
**Why it happens:** Not understanding which transport their client supports
**How to avoid:** Clearly label sections "Claude Code (stdio)" and "Claude Desktop (HTTP)"
**Warning signs:** "Unknown transport" or connection issues

## Code Examples

### Docker Run Examples

**Minimal daemon mode (Claude Desktop path):**
```bash
# Source: Phase 24 Dockerfile and s6 service definitions
docker run -d \
  --name cocosearch \
  -v cocosearch-data:/data \
  -v "$PWD":/mnt/repos:ro \
  -p 3000:3000 \
  cocosearch
```

**Interactive stdio mode (Claude Code path):**
```bash
# Source: Phase 24 container design
docker run -i \
  --name cocosearch \
  -v cocosearch-data:/data \
  -v "$PWD":/mnt/repos:ro \
  cocosearch \
  cocosearch mcp --transport stdio
```

### Claude Code MCP Configuration

**JSON config format:**
```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "cocosearch-data:/data",
        "-v", "/absolute/path/to/repos:/mnt/repos:ro",
        "cocosearch",
        "cocosearch", "mcp", "--transport", "stdio"
      ]
    }
  }
}
```

**CLI command format:**
```bash
# Source: https://code.claude.com/docs/en/mcp
claude mcp add --transport stdio cocosearch -- \
  docker run -i --rm \
  -v cocosearch-data:/data \
  -v "$PWD":/mnt/repos:ro \
  cocosearch cocosearch mcp --transport stdio
```

### Claude Desktop MCP Configuration

**Via mcp-remote (HTTP transport):**
```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:3000/mcp"]
    }
  }
}
```

Requires running container as daemon first:
```bash
docker run -d -p 3000:3000 -v cocosearch-data:/data cocosearch
```

### Troubleshooting Commands

```bash
# Check container status
docker ps -a | grep cocosearch

# View logs (first diagnostic step)
docker logs cocosearch

# Check health status
docker inspect cocosearch --format='{{.State.Health.Status}}'

# Interactive debug
docker exec -it cocosearch sh
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE transport primary | Streamable HTTP preferred | Q4 2025 | SSE may be deprecated, document HTTP as primary |
| Direct HTTP in Desktop config | mcp-remote proxy required | Current | Desktop only supports stdio natively |
| Manual PostgreSQL + Ollama | All-in-one Docker container | Phase 24 | Simpler deployment |

**Deprecated/outdated:**
- SSE transport: Still works but HTTP is preferred and more reliable
- Direct HTTP config in Claude Desktop: Never worked for remote servers, requires proxy

## Open Questions

1. **mcp-remote vs mcp-proxy preference**
   - What we know: Both work, mcp-remote is more widely documented
   - What's unclear: Which is officially recommended by Anthropic
   - Recommendation: Document mcp-remote as primary, mention mcp-proxy as alternative

2. **Exact volume path for repo-local data**
   - What we know: CONTEXT.md says "repo-local folder added to .gitignore"
   - What's unclear: Exact path name (e.g., `.cocosearch-data/` or `cocosearch-data/`)
   - Recommendation: Use `.cocosearch-data/` (hidden, consistent with other tool patterns)

3. **GPU passthrough documentation**
   - What we know: Deferred to future (DOCK-09)
   - What's unclear: Whether to mention it exists at all
   - Recommendation: Skip entirely per scope, users can check Ollama docs

## Sources

### Primary (HIGH confidence)
- Claude Code MCP Documentation: https://code.claude.com/docs/en/mcp - Transport types, configuration format, CLI commands
- Project Dockerfile: `/Users/fedorzhdanov/GIT/personal/coco-s/docker/Dockerfile` - Container ports, volumes, environment variables
- Project MCP Server: `/Users/fedorzhdanov/GIT/personal/coco-s/src/cocosearch/mcp/server.py` - Transport options (stdio, sse, http)
- Phase CONTEXT.md: `/Users/fedorzhdanov/GIT/personal/coco-s/.planning/phases/26-documentation-polish/26-CONTEXT.md` - User decisions

### Secondary (MEDIUM confidence)
- Claude Desktop Remote MCP: https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers - Remote server limitations
- mcp-remote npm: https://www.npmjs.com/package/mcp-remote - Proxy tool for Claude Desktop
- Docker Best Practices: https://docs.docker.com/build/building/best-practices/ - Volume patterns

### Tertiary (LOW confidence)
- Docker troubleshooting patterns from community sources (validated against official docs)

## Metadata

**Confidence breakdown:**
- Documentation patterns: HIGH - Based on official docs and existing README
- Claude Code config: HIGH - Verified with official documentation
- Claude Desktop config: MEDIUM - Remote HTTP requires proxy (verified), exact mcp-remote usage from community
- Troubleshooting: MEDIUM - Based on common Docker patterns, validated against official docs

**Research date:** 2026-02-02
**Valid until:** 60+ days (documentation patterns stable, MCP transport recommendations evolving)
