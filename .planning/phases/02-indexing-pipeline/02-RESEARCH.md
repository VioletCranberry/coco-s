# Phase 2: Indexing Pipeline - Research

**Researched:** 2026-01-24
**Domain:** CocoIndex flow with Tree-sitter chunking, Ollama embeddings, and incremental indexing
**Confidence:** HIGH

## Summary

Phase 2 builds the core indexing pipeline using CocoIndex's declarative flow model. The research confirms that CocoIndex provides built-in Tree-sitter support via `SplitRecursively()` for language-aware chunking, native Ollama integration via `EmbedText()` for embedding generation, and automatic incremental processing with mtime-based change detection. The flow pattern is well-documented and follows a consistent structure: source -> transform -> collect -> export.

Key decisions from CONTEXT.md are fully supported by CocoIndex's capabilities:
- **Hierarchical chunking with metadata**: `SplitRecursively()` preserves AST structure, and the collector can store arbitrary metadata (file path, line range, symbol type, parent chain)
- **Maximum language support**: Tree-sitter integration supports 30+ languages automatically via file extension detection
- **Reference storage**: Only store file path + line range; fetch actual code on demand
- **Incremental updates**: CocoIndex tracks state internally, using mtime for change detection

The primary technical challenge is implementing .gitignore respect, as CocoIndex's `LocalFile` source only provides include/exclude patterns but not automatic .gitignore parsing. The `pathspec` library provides GitIgnoreSpec for this purpose.

**Primary recommendation:** Use CocoIndex's native flow model with `SplitRecursively()` for chunking and `EmbedText(OLLAMA)` for embeddings. Handle .gitignore parsing externally via `pathspec` library before passing patterns to `LocalFile`.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cocoindex | 0.3.28 | Indexing engine | Native Tree-sitter, incremental processing, Ollama support |
| psycopg | 3.3.2 | PostgreSQL driver | Connection pooling for search queries |
| pgvector | 0.4.2 | Vector types | Required for PostgreSQL vector storage |

### Additional Dependencies

| Library | Version | Purpose | Installation |
|---------|---------|---------|--------------|
| pathspec | 1.0.3 | .gitignore parsing | `uv add pathspec` |
| pyyaml | 6.0.2 | Config file parsing | `uv add pyyaml` |
| pydantic | 2.x | Config validation | Already installed (via mcp) |
| rich | 13.x | Progress bars | `uv add rich` |

### Embedding Configuration

| Model | Dimensions | Context | Configuration |
|-------|------------|---------|---------------|
| nomic-embed-text | 768 | 8192 tokens | `EmbedText(api_type=OLLAMA, model="nomic-embed-text")` |

**Note:** nomic-embed-text's 8192 token context (~32KB) easily handles most code chunks. For very large functions (500+ lines), use chunking with overlap rather than truncation.

**Installation:**
```bash
# Additional dependencies for Phase 2
uv add pathspec pyyaml rich
```

## Architecture Patterns

### Recommended Project Structure

```
src/cocosearch/
├── __init__.py
├── indexer/                    # Phase 2 - Indexing Pipeline
│   ├── __init__.py
│   ├── flow.py                 # CocoIndex flow definition
│   ├── chunker.py              # SplitRecursively configuration
│   ├── embedder.py             # EmbedText with Ollama
│   ├── file_filter.py          # .gitignore + pattern handling
│   ├── progress.py             # Progress reporting
│   └── config.py               # Index configuration models
├── storage/                    # Database interaction (Phase 3)
│   ├── __init__.py
│   └── index_manager.py        # Named index lifecycle
└── cli.py                      # CLI entry point
```

### Pattern 1: CocoIndex Flow Definition

**What:** Declarative flow for indexing codebase with Tree-sitter chunking and Ollama embeddings
**When to use:** Core indexing pipeline implementation

**Example:**
```python
# Source: https://cocoindex.io/docs/examples/code_index
import os
import cocoindex

@cocoindex.flow_def(name="CodeIndex_{index_name}")
def create_code_index_flow(flow_builder: cocoindex.FlowBuilder,
                           data_scope: cocoindex.DataScope,
                           codebase_path: str,
                           included_patterns: list[str],
                           excluded_patterns: list[str]):
    # Step 1: Source - read files from codebase
    data_scope["files"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(
            path=codebase_path,
            included_patterns=included_patterns,
            excluded_patterns=excluded_patterns,
        )
    )

    # Step 2: Create collector for embeddings
    code_embeddings = data_scope.add_collector()

    # Step 3: Process each file
    with data_scope["files"].row() as file:
        # Extract extension for language detection
        file["extension"] = file["filename"].transform(extract_extension)

        # Chunk using Tree-sitter
        file["chunks"] = file["content"].transform(
            cocoindex.functions.SplitRecursively(),
            language=file["extension"],
            chunk_size=1000,
            chunk_overlap=300,
        )

        # Process each chunk
        with file["chunks"].row() as chunk:
            # Generate embedding via Ollama
            chunk["embedding"] = chunk["text"].transform(
                cocoindex.functions.EmbedText(
                    api_type=cocoindex.LlmApiType.OLLAMA,
                    model="nomic-embed-text",
                )
            )

            # Collect with metadata
            code_embeddings.collect(
                filename=file["filename"],
                location=chunk["location"],
                embedding=chunk["embedding"],
            )

    # Step 4: Export to PostgreSQL
    code_embeddings.export(
        f"{index_name}_chunks",
        cocoindex.storages.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndexDef(
                "embedding",
                cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY
            )
        ],
    )
```

### Pattern 2: .gitignore + Pattern Filtering

**What:** Parse .gitignore and combine with user include/exclude patterns
**When to use:** Before creating LocalFile source

**Example:**
```python
# Source: https://github.com/cpburnz/python-pathspec
from pathlib import Path
from pathspec import GitIgnoreSpec

def load_gitignore_patterns(codebase_path: str) -> list[str]:
    """Load patterns from .gitignore if it exists."""
    gitignore_path = Path(codebase_path) / ".gitignore"
    if gitignore_path.exists():
        return gitignore_path.read_text().splitlines()
    return []

def build_exclude_patterns(
    codebase_path: str,
    user_excludes: list[str] | None = None,
) -> list[str]:
    """Combine .gitignore patterns with user excludes and defaults."""
    # Default excludes (always applied)
    defaults = [
        ".*",                    # Hidden files/dirs
        "**/node_modules",       # Node.js
        "**/__pycache__",        # Python
        "**/target",             # Rust
        "**/vendor",             # Go, PHP
        "**/*.min.js",           # Minified JS
        "**/*.min.css",          # Minified CSS
    ]

    # Load .gitignore patterns
    gitignore = load_gitignore_patterns(codebase_path)

    # Combine all patterns
    all_excludes = defaults + gitignore + (user_excludes or [])

    # Remove empty lines and comments
    return [p for p in all_excludes if p and not p.startswith("#")]
```

### Pattern 3: Transform Flow for Shared Embedding

**What:** Reusable embedding function for both indexing and querying
**When to use:** Always - ensures consistent embeddings between index and search

**Example:**
```python
# Source: https://cocoindex.io/docs/examples/code_index
import cocoindex

@cocoindex.transform_flow()
def code_to_embedding(text: cocoindex.DataSlice[str]) -> cocoindex.DataSlice[list[float]]:
    """Shared embedding function for indexing and querying."""
    return text.transform(
        cocoindex.functions.EmbedText(
            api_type=cocoindex.LlmApiType.OLLAMA,
            model="nomic-embed-text",
        )
    )

# Usage in indexing flow:
chunk["embedding"] = chunk["text"].call(code_to_embedding)

# Usage in search:
query_embedding = code_to_embedding.eval("search query text")
```

### Pattern 4: Reference-Only Storage

**What:** Store file path + line range, not full chunk text
**When to use:** Per CONTEXT.md decision - read file on demand

**Example:**
```python
# Store only references (location contains line/column info)
code_embeddings.collect(
    filename=file["filename"],
    location=chunk["location"],  # Contains offset, line, column
    embedding=chunk["embedding"],
    # Optionally: symbol_name, symbol_type, parent_chain for metadata
)

# On retrieval: read actual code from file
def get_chunk_code(filename: str, location: dict) -> str:
    """Read chunk code from file using stored location."""
    with open(filename) as f:
        lines = f.readlines()
    start_line = location["start"]["line"]
    end_line = location["end"]["line"]
    return "".join(lines[start_line:end_line + 1])
```

### Pattern 5: Config File for Defaults

**What:** .cocosearch.yaml for project-level defaults
**When to use:** Per CONTEXT.md - config file for defaults, CLI can override

**Example:**
```yaml
# .cocosearch.yaml
indexing:
  include_patterns:
    - "*.py"
    - "*.js"
    - "*.ts"
    - "*.rs"
    - "*.go"
    - "*.md"
  exclude_patterns:
    - "**/test/**"
    - "**/*_test.py"
  chunk_size: 1000
  chunk_overlap: 300

# Loaded with pydantic + pyyaml
```

```python
from pathlib import Path
from pydantic import BaseModel
import yaml

class IndexingConfig(BaseModel):
    include_patterns: list[str] = ["*.py", "*.js", "*.ts", "*.rs", "*.go", "*.md"]
    exclude_patterns: list[str] = []
    chunk_size: int = 1000
    chunk_overlap: int = 300

def load_config(codebase_path: str) -> IndexingConfig:
    config_path = Path(codebase_path) / ".cocosearch.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return IndexingConfig(**data.get("indexing", {}))
    return IndexingConfig()
```

### Anti-Patterns to Avoid

- **Fixed-token chunking for code:** Use `SplitRecursively()` with language parameter for AST-aware chunking
- **Different embedding models for index vs query:** Use `@cocoindex.transform_flow()` to share exact same embedding
- **Storing full chunk text:** Store references only; read file on demand (saves storage, always current)
- **Ignoring .gitignore:** Parse and apply .gitignore patterns; users expect this behavior
- **Blocking on large codebases:** Report progress during indexing; skip problematic files

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Code chunking | Regex-based splitter | `SplitRecursively()` with Tree-sitter | Respects AST, handles 30+ languages, battle-tested |
| Language detection | Extension map | `SplitRecursively(language=extension)` | CocoIndex auto-detects from extension |
| Incremental indexing | File hash tracking | CocoIndex internal state | Handles mtime, dependency graph, deleted files |
| .gitignore parsing | Custom parser | `pathspec.GitIgnoreSpec` | Handles edge cases Git does, actively maintained |
| Embedding generation | Direct HTTP to Ollama | `EmbedText(api_type=OLLAMA)` | Batching, error handling, retry built-in |
| Progress bars | Custom print statements | `rich.progress` or `tqdm` | Async-safe, nested bars, time estimates |
| Config validation | Manual dict parsing | Pydantic models | Type safety, defaults, nested structures |

**Key insight:** CocoIndex handles the hard parts (Tree-sitter integration, incremental state, embedding batching). Focus on the integration layer: file filtering, progress reporting, CLI interface.

## Common Pitfalls

### Pitfall 1: Not Initializing CocoIndex

**What goes wrong:** Flow operations fail with cryptic errors about missing database connection.

**Why it happens:** CocoIndex requires initialization before flow operations.

**How to avoid:**
```python
import cocoindex

# Initialize from environment variable
cocoindex.init()  # Reads COCOINDEX_DATABASE_URL

# Or explicit settings
cocoindex.init(
    cocoindex.Settings(
        database=cocoindex.DatabaseConnectionSpec(
            url="postgresql://cocoindex:cocoindex@localhost:5432/cocoindex"
        )
    )
)
```

**Warning signs:** "Settings not initialized" or database connection errors.

### Pitfall 2: Flow Name Collisions

**What goes wrong:** Multiple indexes overwrite each other's data.

**Why it happens:** CocoIndex uses flow name to identify persistent state and target tables.

**How to avoid:** Include index name in flow name:
```python
@cocoindex.flow_def(name=f"CodeIndex_{index_name}")
def create_flow(...):
    ...
```

**Warning signs:** Data from one codebase appearing in another index's results.

### Pitfall 3: Chunk Size vs Token Limit Mismatch

**What goes wrong:** Very large chunks get truncated by embedding model, losing semantic meaning.

**Why it happens:** `chunk_size` in `SplitRecursively()` is in bytes, not tokens. nomic-embed-text has 8192 token (~32KB) limit.

**How to avoid:**
- Set `chunk_size=1000` (bytes) with `chunk_overlap=300`
- For 500+ line functions, Tree-sitter will chunk at logical boundaries
- nomic-embed-text handles up to ~32KB; 1000-byte chunks are well within limit

**Warning signs:** Embeddings for large files don't match semantically similar queries.

### Pitfall 4: Missing max_file_size for Binary Files

**What goes wrong:** Indexer tries to read large binary files, causing memory issues or failures.

**Why it happens:** LocalFile source reads all matching files by default.

**How to avoid:**
```python
cocoindex.sources.LocalFile(
    path=codebase_path,
    included_patterns=["*.py", "*.js"],  # Only code files
    excluded_patterns=["*.exe", "*.dll", "*.so"],
    max_file_size=1_000_000,  # 1MB limit
)
```

**Warning signs:** Memory spikes, timeouts, or encoding errors during indexing.

### Pitfall 5: Not Handling Deleted Files

**What goes wrong:** Deleted files remain in index, returning stale results.

**Why it happens:** Incremental updates add/update but may miss deletions if not properly tracked.

**How to avoid:** CocoIndex handles this automatically via lineage tracking. Ensure you use `flow.update()` not custom logic:
```python
# This handles deletions automatically
update_stats = code_index_flow.update(print_stats=True)
# Output includes: "files: X added, Y removed, Z updated"
```

**Warning signs:** Search returns results from files that no longer exist.

### Pitfall 6: Blocking MCP Tool During Long Index

**What goes wrong:** MCP client times out waiting for large codebase indexing.

**Why it happens:** Indexing runs synchronously, blocking the MCP tool response.

**How to avoid:** For Phase 2, indexing is CLI/API triggered (not MCP). For Phase 3 MCP integration:
- Report progress via MCP notifications
- Consider async indexing with status polling

**Warning signs:** MCP client disconnects during large indexing operations.

## Code Examples

Verified patterns from official sources:

### Complete Indexing Flow

```python
# Source: https://cocoindex.io/docs/examples/code_index
import os
import cocoindex

@cocoindex.op.function()
def extract_extension(filename: str) -> str:
    """Extract file extension for language detection."""
    return os.path.splitext(filename)[1]

@cocoindex.transform_flow()
def code_to_embedding(text: cocoindex.DataSlice[str]) -> cocoindex.DataSlice[list[float]]:
    """Shared embedding function."""
    return text.transform(
        cocoindex.functions.EmbedText(
            api_type=cocoindex.LlmApiType.OLLAMA,
            model="nomic-embed-text",
        )
    )

@cocoindex.flow_def(name="CodeEmbedding")
def code_embedding_flow(flow_builder: cocoindex.FlowBuilder,
                        data_scope: cocoindex.DataScope):
    # Add source
    data_scope["files"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(
            path=os.path.join("..", ".."),
            included_patterns=["*.py", "*.rs", "*.toml", "*.md", "*.mdx"],
            excluded_patterns=[".*", "target", "**/node_modules"],
        )
    )

    code_embeddings = data_scope.add_collector()

    with data_scope["files"].row() as file:
        file["extension"] = file["filename"].transform(extract_extension)
        file["chunks"] = file["content"].transform(
            cocoindex.functions.SplitRecursively(),
            language=file["extension"],
            chunk_size=1000,
            chunk_overlap=300,
        )

        with file["chunks"].row() as chunk:
            chunk["embedding"] = chunk["text"].call(code_to_embedding)
            code_embeddings.collect(
                filename=file["filename"],
                location=chunk["location"],
                code=chunk["text"],
                embedding=chunk["embedding"],
            )

    code_embeddings.export(
        "code_embeddings",
        cocoindex.storages.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndexDef(
                "embedding",
                cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY
            )
        ],
    )
```

### Running Flow Update

```python
# Source: https://cocoindex.io/docs/core/flow_methods
import cocoindex

# Initialize
cocoindex.init()

# Setup flow (creates tables)
code_embedding_flow.setup(report_to_stdout=True)

# Run indexing
update_info = code_embedding_flow.update(print_stats=True)
# Output: files: 42 added, 0 removed, 0 updated
```

### CLI Usage

```bash
# Source: https://cocoindex.io/docs/core/flow_methods
# Setup and update in one command
cocoindex update --setup main.py

# Just update (after initial setup)
cocoindex update main.py

# Force re-export (rebuild target)
cocoindex update --reexport main.py
```

### .gitignore Parsing with pathspec

```python
# Source: https://github.com/cpburnz/python-pathspec
from pathlib import Path
from pathspec import GitIgnoreSpec

def should_include_file(filepath: str, codebase_root: str) -> bool:
    """Check if file should be indexed based on .gitignore."""
    gitignore_path = Path(codebase_root) / ".gitignore"

    if not gitignore_path.exists():
        return True

    patterns = gitignore_path.read_text().splitlines()
    spec = GitIgnoreSpec.from_lines(patterns)

    relative_path = Path(filepath).relative_to(codebase_root)
    return not spec.match_file(str(relative_path))
```

### Progress Reporting with Rich

```python
# Source: https://rich.readthedocs.io/
from rich.progress import Progress, SpinnerColumn, TextColumn

def index_with_progress(files: list[str]):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Indexing...", total=len(files))

        for file in files:
            progress.update(task, description=f"Indexing {file}")
            # ... indexing logic ...
            progress.advance(task)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Regex-based code splitting | Tree-sitter AST chunking | 2024 | Semantic boundaries preserved |
| Manual change detection | CocoIndex incremental processing | CocoIndex 0.2+ | Automatic mtime + lineage tracking |
| OpenAI embeddings | Local Ollama + nomic-embed-text | 2024-2025 | Free, private, 8K context |
| Storing full text chunks | Reference storage (file + line range) | Best practice | Smaller index, always current |
| Manual gitignore parsing | pathspec.GitIgnoreSpec | 2025 | Accurate Git behavior replication |

**Deprecated/outdated:**
- `SentenceTransformerEmbed`: Still works, but `EmbedText(OLLAMA)` preferred for consistency with Ollama
- Custom file watchers: CocoIndex handles live updates via `FlowLiveUpdater`
- Storing chunk text: Reference-only storage is more efficient

## Open Questions

Things that couldn't be fully resolved:

1. **Hierarchical context in embeddings**
   - What we know: CONTEXT.md specifies "methods include parent class name/signature as context"
   - What's unclear: Exact implementation - prepend parent signature to chunk text before embedding?
   - Recommendation: Prepend parent chain to chunk text: `"class Foo:\n  def bar(self):\n    ..."` before embedding

2. **Symbol extraction from Tree-sitter**
   - What we know: Tree-sitter provides AST with node types (function_definition, class_definition)
   - What's unclear: Whether CocoIndex exposes node type in `location` or if custom function needed
   - Recommendation: Test SplitRecursively output; may need custom Tree-sitter function for symbol metadata

3. **Index name derivation edge cases**
   - What we know: Auto-derive from directory path (e.g., /home/user/myproject -> 'myproject')
   - What's unclear: Handling of special characters, duplicates, very long paths
   - Recommendation: Sanitize to alphanumeric + underscores; allow explicit override

4. **Very large function handling (500+ lines)**
   - What we know: nomic-embed-text handles 8192 tokens (~32KB); SplitRecursively respects chunk_size
   - What's unclear: Whether very large single functions (>8K tokens) need special handling
   - Recommendation: Let SplitRecursively split at nested boundaries; 1000-byte chunk_size prevents oversized chunks

## Sources

### Primary (HIGH confidence)
- [CocoIndex Functions](https://cocoindex.io/docs/ops/functions) - SplitRecursively parameters and language support
- [CocoIndex LLM Support](https://cocoindex.io/docs/ai/llm) - EmbedText with Ollama configuration
- [CocoIndex Flow Definition](https://cocoindex.io/docs/core/flow_def) - FlowBuilder, DataScope, collectors
- [CocoIndex Flow Methods](https://cocoindex.io/docs/core/flow_methods) - setup(), update(), FlowLiveUpdater
- [CocoIndex Code Indexing Example](https://cocoindex.io/docs/examples/code_index) - Complete reference implementation
- [CocoIndex Incremental Processing](https://cocoindex.io/blogs/incremental-processing) - Change detection, state tracking
- [pathspec PyPI](https://pypi.org/project/pathspec/) - GitIgnoreSpec for .gitignore parsing

### Secondary (MEDIUM confidence)
- [CocoIndex GitHub](https://github.com/cocoindex-io/cocoindex) - Latest features and API
- [nomic-embed-text HuggingFace](https://huggingface.co/nomic-ai/nomic-embed-text-v1) - 8192 token context
- [pathspec GitHub](https://github.com/cpburnz/python-pathspec) - GitIgnoreSpec edge cases
- [Rich Progress](https://rich.readthedocs.io/) - Progress bar patterns

### Tertiary (LOW confidence)
- CocoIndex Medium articles - Implementation insights, may be outdated
- Community implementations (aanno/cocoindex-code-mcp-server) - Reference, not authoritative

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components verified via official CocoIndex documentation
- Architecture: HIGH - Based on official examples and API documentation
- Pitfalls: HIGH - Based on official troubleshooting and documented behaviors
- Code examples: HIGH - From official CocoIndex documentation

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - CocoIndex is stable, frequent minor updates)
