# Phase 1: Foundation - Research

**Researched:** 2026-01-24
**Domain:** Development environment infrastructure (PostgreSQL/pgvector, Ollama, UV/Python)
**Confidence:** HIGH

## Summary

Phase 1 establishes the development environment with three core infrastructure components: PostgreSQL with pgvector for vector storage, Ollama for local embeddings, and a UV-managed Python project. The research confirms all stack choices from prior research are well-supported with official Docker images, clear configuration patterns, and established verification procedures.

The foundation phase is primarily configuration and verification work, not code development. The key challenge is ensuring all services are properly configured, running, and verified before moving to indexing pipeline work. Docker Compose with health checks provides the orchestration pattern for service dependencies.

**Primary recommendation:** Use Docker Compose with health checks to orchestrate PostgreSQL and verification scripts. Verify each component independently before integrating with CocoIndex.

## Standard Stack

The established libraries/tools for this domain:

### Core Infrastructure

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| PostgreSQL | 17 | Database | Latest stable, required by CocoIndex for incremental processing |
| pgvector | 0.8.1 | Vector extension | Pre-installed in `pgvector/pgvector:pg17` image, supports HNSW indexing |
| Ollama | latest | Embedding runtime | Runs nomic-embed-text locally, OpenAI-compatible API |
| nomic-embed-text | v1.5 | Embedding model | 768 dimensions, 8192 token context, best for code (per Continue.dev) |
| UV | 0.9.26 | Package manager | Project requirement, 10-100x faster than pip |
| Python | 3.11+ | Runtime | CocoIndex minimum requirement |

### Python Dependencies

| Library | Version | Purpose | Installation |
|---------|---------|---------|--------------|
| cocoindex | 0.3.28 | Indexing engine | `uv add cocoindex[embeddings]` |
| psycopg | 3.3.2 | PostgreSQL driver | `uv add "psycopg[binary,pool]"` |
| pgvector | 0.4.2 | Vector type support | `uv add pgvector` |
| mcp | 1.26.0 | MCP SDK | `uv add "mcp[cli]"` |

### Docker Images

| Image | Tag | Purpose |
|-------|-----|---------|
| pgvector/pgvector | pg17 | PostgreSQL 17 with pgvector pre-installed |

**Installation:**
```bash
# Initialize Python project
uv init cocosearch --python 3.11
cd cocosearch

# Core dependencies
uv add cocoindex[embeddings]
uv add "mcp[cli]"
uv add "psycopg[binary,pool]"
uv add pgvector

# Dev dependencies
uv add --dev pytest ruff

# Pull embedding model
ollama pull nomic-embed-text
```

## Architecture Patterns

### Recommended Project Structure
```
cocosearch/
├── docker-compose.yml      # PostgreSQL + pgvector
├── pyproject.toml          # UV project config
├── uv.lock                  # Dependency lockfile (auto-generated)
├── .python-version          # Python version (auto-generated)
├── .env                     # Environment variables
├── .env.example             # Template for .env
├── src/
│   └── cocosearch/
│       ├── __init__.py
│       └── ...
├── scripts/
│   └── verify_setup.py      # Infrastructure verification
└── tests/
    └── test_foundation.py   # Foundation tests
```

### Pattern 1: Docker Compose with Health Checks

**What:** Use Docker Compose with health checks to ensure PostgreSQL is ready before dependent services start.

**When to use:** Always for local development. Services that depend on PostgreSQL should wait for it to be healthy.

**Example:**
```yaml
# docker-compose.yml
# Source: https://docs.docker.com/compose/how-tos/startup-order/
services:
  db:
    image: pgvector/pgvector:pg17
    container_name: cocosearch-db
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: cocoindex
      POSTGRES_PASSWORD: cocoindex
      POSTGRES_DB: cocoindex
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cocoindex -d cocoindex"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  postgres_data:
```

### Pattern 2: Environment Configuration

**What:** Use `.env` file for CocoIndex database configuration.

**When to use:** All CocoIndex projects. CocoIndex automatically loads from `.env`.

**Example:**
```bash
# .env
# Source: https://cocoindex.io/docs/core/settings
COCOINDEX_DATABASE_URL=postgresql://cocoindex:cocoindex@localhost:5432/cocoindex
```

### Pattern 3: pgvector Extension Initialization

**What:** Create the vector extension in PostgreSQL on first setup.

**When to use:** After PostgreSQL container starts, before running CocoIndex.

**Example:**
```sql
-- Run once after PostgreSQL is ready
-- Source: https://github.com/pgvector/pgvector
CREATE EXTENSION IF NOT EXISTS vector;
```

**Verification:**
```bash
# Verify extension is installed
docker exec cocosearch-db psql -U cocoindex -d cocoindex -c \
  "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

### Pattern 4: Ollama Embedding Verification

**What:** Verify Ollama is running and nomic-embed-text returns 768-dimensional embeddings.

**When to use:** After pulling the model, before CocoIndex integration.

**Example:**
```bash
# Source: https://docs.ollama.com/capabilities/embeddings
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify embedding dimensions
curl -s http://localhost:11434/api/embed \
  -d '{"model": "nomic-embed-text", "input": "test"}' | \
  python -c "import sys,json; e=json.load(sys.stdin)['embeddings'][0]; print(f'Dimensions: {len(e)}')"
# Should output: Dimensions: 768
```

### Pattern 5: UV Project Initialization

**What:** Initialize a UV-managed Python project with proper structure.

**When to use:** Starting the project.

**Example:**
```bash
# Source: https://docs.astral.sh/uv/guides/projects/
# Initialize as an application (not library)
uv init cocosearch --python 3.11

# Or with src layout for better organization
uv init cocosearch --python 3.11 --package
```

### Anti-Patterns to Avoid

- **No health checks on PostgreSQL:** Using `depends_on` without `condition: service_healthy` - services may fail because PostgreSQL isn't ready yet
- **Hardcoded database URLs:** Putting connection strings directly in code instead of environment variables
- **Using pip instead of UV:** Project requires UV for package management
- **Skipping extension verification:** Assuming pgvector is enabled without checking
- **External API calls for embeddings:** Using OpenAI or other cloud APIs instead of local Ollama

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PostgreSQL + pgvector setup | Custom Dockerfile with extension compilation | `pgvector/pgvector:pg17` image | Extension pre-compiled, tested, maintained |
| Database health checks | Custom TCP/HTTP checks | `pg_isready` command | Official PostgreSQL tool, handles all edge cases |
| Environment configuration | Custom config loading | `.env` file + CocoIndex auto-loading | CocoIndex reads `COCOINDEX_*` variables automatically |
| Embedding generation | Direct HuggingFace integration | Ollama with nomic-embed-text | Ollama handles model management, GPU acceleration |
| Python virtual environments | Manual venv management | UV | UV manages everything: venv, packages, lockfile |

**Key insight:** Phase 1 is infrastructure assembly, not code development. Use official images and established patterns.

## Common Pitfalls

### Pitfall 1: PostgreSQL Container Not Ready

**What goes wrong:** Scripts or services try to connect before PostgreSQL accepts connections, causing connection refused errors.

**Why it happens:** Docker Compose `depends_on` only waits for container start, not service readiness. PostgreSQL needs time to initialize.

**How to avoid:** Use health check with `pg_isready`:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U cocoindex -d cocoindex"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

**Warning signs:** "connection refused" or "the database system is starting up" errors.

### Pitfall 2: pgvector Extension Not Enabled

**What goes wrong:** Queries using `vector` type fail with "type 'vector' does not exist".

**Why it happens:** pgvector image includes the extension but doesn't enable it by default. `CREATE EXTENSION vector` must be run per database.

**How to avoid:** Add initialization script or explicit verification step:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Warning signs:** SQL errors mentioning unknown type or function (e.g., `<=>` operator).

### Pitfall 3: Ollama Model Not Pulled

**What goes wrong:** Embedding requests fail with "model not found".

**Why it happens:** Ollama must download models before use. `ollama pull` is required.

**How to avoid:** Verify model availability:
```bash
# Check model is available
curl http://localhost:11434/api/tags | grep nomic-embed-text
```

**Warning signs:** Empty models list or HTTP 404/500 errors from Ollama.

### Pitfall 4: Wrong Embedding Dimensions

**What goes wrong:** CocoIndex or pgvector throws dimension mismatch errors.

**Why it happens:** Different models have different dimensions. Database column must match model output.

**How to avoid:** Verify nomic-embed-text returns 768 dimensions:
```bash
curl -s http://localhost:11434/api/embed \
  -d '{"model": "nomic-embed-text", "input": "test"}' | \
  python -c "import sys,json; print(len(json.load(sys.stdin)['embeddings'][0]))"
```

**Warning signs:** Dimension errors in CocoIndex or pgvector.

### Pitfall 5: UV Lock File Not Committed

**What goes wrong:** Different environments get different dependency versions.

**Why it happens:** `uv.lock` ensures reproducible installs but is sometimes ignored.

**How to avoid:** Always commit `uv.lock` to version control.

**Warning signs:** "it works on my machine" issues, different behavior across environments.

### Pitfall 6: Docker Desktop Version Too Old

**What goes wrong:** pgvector container fails to start or behaves unexpectedly.

**Why it happens:** pgvector/pgvector Docker image requires Docker Desktop 4.37.1 or later.

**How to avoid:** Verify Docker Desktop version before setup.

**Warning signs:** Container crashes, unexpected errors during pgvector operations.

## Code Examples

Verified patterns from official sources:

### Complete Docker Compose Setup

```yaml
# docker-compose.yml
# Source: https://docs.docker.com/compose/how-tos/startup-order/
# Source: https://github.com/pgvector/pgvector
version: "3.8"

services:
  db:
    image: pgvector/pgvector:pg17
    container_name: cocosearch-db
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: cocoindex
      POSTGRES_PASSWORD: cocoindex
      POSTGRES_DB: cocoindex
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cocoindex -d cocoindex"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped

volumes:
  postgres_data:
```

### Environment File Template

```bash
# .env.example
# Source: https://cocoindex.io/docs/core/settings

# Required: PostgreSQL connection
COCOINDEX_DATABASE_URL=postgresql://cocoindex:cocoindex@localhost:5432/cocoindex

# Optional: Connection pool settings (defaults shown)
# COCOINDEX_DATABASE_MAX_CONNECTIONS=25
# COCOINDEX_DATABASE_MIN_CONNECTIONS=5
```

### Verification Script

```python
#!/usr/bin/env python3
"""Verify Phase 1 infrastructure setup."""
# scripts/verify_setup.py

import subprocess
import sys
import json
import urllib.request

def check_postgres() -> bool:
    """Verify PostgreSQL is running with pgvector."""
    try:
        result = subprocess.run(
            [
                "docker", "exec", "cocosearch-db",
                "psql", "-U", "cocoindex", "-d", "cocoindex", "-t", "-c",
                "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        if version:
            print(f"[OK] PostgreSQL with pgvector {version}")
            return True
        else:
            print("[FAIL] pgvector extension not enabled")
            return False
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] PostgreSQL check failed: {e}")
        return False

def check_ollama() -> bool:
    """Verify Ollama is running with nomic-embed-text."""
    try:
        # Check Ollama is running
        with urllib.request.urlopen("http://localhost:11434/api/tags") as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            if any("nomic-embed-text" in m for m in models):
                print(f"[OK] Ollama running with nomic-embed-text")
            else:
                print(f"[FAIL] nomic-embed-text not found. Available: {models}")
                return False

        # Verify embedding dimensions
        req = urllib.request.Request(
            "http://localhost:11434/api/embed",
            data=json.dumps({"model": "nomic-embed-text", "input": "test"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            dims = len(data["embeddings"][0])
            if dims == 768:
                print(f"[OK] nomic-embed-text returns {dims} dimensions")
                return True
            else:
                print(f"[FAIL] Expected 768 dimensions, got {dims}")
                return False
    except Exception as e:
        print(f"[FAIL] Ollama check failed: {e}")
        return False

def check_python_deps() -> bool:
    """Verify Python dependencies are installed."""
    try:
        import cocoindex
        import psycopg
        import pgvector
        print(f"[OK] Python dependencies installed (cocoindex {cocoindex.__version__})")
        return True
    except ImportError as e:
        print(f"[FAIL] Missing Python dependency: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=== Phase 1 Foundation Verification ===\n")

    results = [
        check_postgres(),
        check_ollama(),
        check_python_deps(),
    ]

    print()
    if all(results):
        print("All checks passed! Foundation is ready.")
        return 0
    else:
        print("Some checks failed. See above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### CocoIndex Connection Test

```python
# Source: https://cocoindex.io/docs/core/settings
import cocoindex

# Initialize CocoIndex (reads from COCOINDEX_DATABASE_URL)
cocoindex.init()

# Or with explicit settings
cocoindex.init(
    cocoindex.Settings(
        database=cocoindex.DatabaseConnectionSpec(
            url="postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
        )
    )
)
```

### Embedding Test with CocoIndex

```python
# Source: https://cocoindex.io/docs/ai/llm
import cocoindex

# Configure Ollama embedding
embedding_fn = cocoindex.functions.EmbedText(
    api_type=cocoindex.LlmApiType.OLLAMA,
    model="nomic-embed-text",
    address="http://localhost:11434",  # Optional, this is the default
)

# Test embedding
vector = embedding_fn.eval("Hello, world!")
print(f"Embedding dimensions: {len(vector)}")  # Should be 768
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual pgvector compilation | `pgvector/pgvector:pg17` image | 2024 | No build step needed |
| `depends_on: [service]` | `depends_on: condition: service_healthy` | Docker Compose 2.x | Proper startup ordering |
| pip + requirements.txt | UV with pyproject.toml | 2024-2025 | 10-100x faster, universal lockfile |
| OpenAI embeddings | Ollama + nomic-embed-text | 2024 | Local-first, free, private |
| `/api/embeddings` | `/api/embed` | Ollama 0.1.26+ | New endpoint format |

**Deprecated/outdated:**
- `ankane/pgvector` image: Use `pgvector/pgvector` (official)
- Ollama `/api/embeddings` endpoint: Use `/api/embed` instead
- pipenv/poetry for new projects: UV is faster and simpler

## Open Questions

Things that couldn't be fully resolved:

1. **Ollama Docker integration**
   - What we know: Ollama can run in Docker, but setup is more complex than native install
   - What's unclear: Whether Docker-based Ollama is better than native for this use case
   - Recommendation: Use native Ollama install for Phase 1 simplicity; Docker can be explored later

2. **PostgreSQL persistence across container rebuilds**
   - What we know: Named volumes persist data, but schema changes may need migration
   - What's unclear: How CocoIndex handles schema migrations on update
   - Recommendation: Use named volume; trust CocoIndex's schema management

3. **Connection pool sizing**
   - What we know: CocoIndex defaults to min=5, max=25 connections
   - What's unclear: Optimal sizing for single-developer local use
   - Recommendation: Use defaults; tune only if issues arise

## Sources

### Primary (HIGH confidence)
- [pgvector GitHub](https://github.com/pgvector/pgvector) - Extension installation and usage
- [pgvector Docker Hub](https://hub.docker.com/r/pgvector/pgvector) - Official Docker image
- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/) - Health check patterns
- [UV Projects Guide](https://docs.astral.sh/uv/guides/projects/) - Project initialization
- [CocoIndex Settings](https://cocoindex.io/docs/core/settings) - Database configuration
- [CocoIndex LLM Support](https://cocoindex.io/docs/ai/llm) - EmbedText with Ollama
- [Ollama Embeddings](https://docs.ollama.com/capabilities/embeddings) - Embedding API
- [Ollama API Tags](https://docs.ollama.com/api/tags) - List models endpoint

### Secondary (MEDIUM confidence)
- [Ollama GitHub API docs](https://github.com/ollama/ollama/blob/main/docs/api.md) - Full API reference
- [Ollama health check issue](https://github.com/ollama/ollama/issues/1378) - Health endpoint discussion

### Tertiary (LOW confidence)
- Community blog posts on pgvector setup - General patterns verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components verified via official documentation
- Architecture: HIGH - Docker Compose patterns from official Docker docs
- Pitfalls: HIGH - Based on official troubleshooting and known issues

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - stable infrastructure components)
