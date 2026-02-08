## Dogfooding

CocoSearch uses CocoSearch to index its own codebase. This demonstrates real-world usage and lets you explore the implementation.

### Indexing the Codebase

```bash
uv run cocosearch index . --name self
```

Expected output:

```
Using index name: self
Indexing .
Indexed 45 files (287 chunks)
```

### Verifying Indexing

```bash
uv run cocosearch stats self --pretty
```

Output shows file count, chunk count, and index size:

```
    Index: self
┏━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric  ┃ Value     ┃
┡━━━━━━━━━╇━━━━━━━━━━━┩
│ Files   │ 45        │
│ Chunks  │ 287       │
│ Size    │ 1.2 MB    │
└─────────┴───────────┘
```

### Example Searches

**Find embedding implementation:**

```bash
uv run cocosearch search "how does embedding work" --index self --pretty
```

Finds the embedder module and Ollama integration:

```
[1] src/cocosearch/indexer/embedder.py:15-45 (score: 0.91)
    class OllamaEmbedder:
        """Generate embeddings using Ollama's nomic-embed-text model."""

        def __init__(self, host: str = "http://localhost:11434"):
            self.host = host
            self.model = "nomic-embed-text"
```

**Search for database operations:**

```bash
uv run cocosearch search "database connection handling" --index self --pretty
```

Finds database initialization and connection management:

```
[1] src/cocosearch/database.py:20-55 (score: 0.88)
    def init_db(database_url: str) -> None:
        """Initialize database with pgvector extension and indexes."""
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
```

**Find Docker setup (filtered by language):**

```bash
uv run cocosearch search "docker setup" --index self --lang bash --pretty
```

Finds the development setup script:

```
[1] dev-setup.sh:45-78 (score: 0.86)
    setup_docker() {
        step "Setting up Docker services"
        if ! docker compose ps | grep -q cocosearch-db; then
            docker compose up -d
        fi
    }
```

**Explore configuration system:**

```bash
uv run cocosearch search "config file discovery" --index self --pretty
```

Finds the configuration loader logic:

```
[1] src/cocosearch/config/loader.py:28-65 (score: 0.89)
    def find_config_file(start_path: Path) -> Path | None:
        """Find cocosearch.yaml in current directory or git root."""
        # Try current directory first
        config_path = start_path / "cocosearch.yaml"
        if config_path.exists():
            return config_path
```
