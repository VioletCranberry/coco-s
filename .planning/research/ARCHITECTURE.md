# Architecture Research: DevOps Language Support Integration

**Domain:** Custom language chunking and metadata extraction for DevOps files (HCL, Dockerfile, Bash)
**Researched:** 2026-01-27
**Confidence:** HIGH (CocoIndex API verified with official docs; codebase integration points verified by reading source)

## Recommended Architecture

The v1.2 DevOps language support integrates into the existing CocoSearch architecture at four points: (1) the `SplitRecursively` constructor gains `custom_languages`, (2) a new metadata extraction step runs inside the CocoIndex flow after chunking, (3) the PostgreSQL collector stores additional metadata columns, and (4) search query and formatters surface metadata in results.

### Integration Overview

```
EXISTING (untouched)                    NEW (v1.2 additions)
========================               ===========================

IndexingConfig                         + DevOps file patterns (*.tf, Dockerfile, *.sh)
    |
    v
create_code_index_flow()
    |
    v
LocalFile source           <unchanged>
    |
    v
SplitRecursively()         + custom_languages=[HCL_SPEC, DOCKERFILE_SPEC, BASH_SPEC]
    |
    v
chunk["text"]              + chunk["metadata"] = extract_devops_metadata(filename, text)
    |
    v
code_to_embedding          <unchanged>
    |
    v
code_embeddings.collect(   + block_type=chunk["metadata"]["block_type"],
    filename, location,    + hierarchy=chunk["metadata"]["hierarchy"],
    embedding              + language_id=chunk["metadata"]["language_id"]
)
    |
    v
PostgreSQL export          + 3 new TEXT columns in chunks table
    |
    v
SearchResult               + block_type, hierarchy, language_id fields
    |
    v
format_json / format_pretty + metadata fields in output
```

### Component Boundaries

| Component | Responsibility | Changes in v1.2 |
|-----------|---------------|------------------|
| **IndexingConfig** (`config.py`) | File include/exclude patterns | Add `*.tf`, `*.hcl`, `Dockerfile*`, `*.sh`, `*.bash` to `include_patterns` |
| **Language definitions** (`languages.py` NEW) | Define `CustomLanguageSpec` for HCL, Dockerfile, Bash | New module with regex separator specs |
| **Metadata extractors** (`metadata.py` NEW) | Extract block_type and hierarchy from chunk text | New module with `@cocoindex.op.function()` |
| **Flow** (`flow.py`) | Orchestrate indexing pipeline | Pass `custom_languages` to `SplitRecursively()`, add metadata extraction step, add new collector fields |
| **SearchResult** (`query.py`) | Search result data class | Add optional `block_type`, `hierarchy`, `language_id` fields |
| **Search SQL** (`query.py`) | PostgreSQL similarity query | SELECT new columns from chunks table |
| **Formatters** (`formatter.py`) | JSON and pretty output | Include metadata in output |
| **MCP server** (`server.py`) | MCP tool responses | Include metadata in search_code return dicts |
| **LANGUAGE_EXTENSIONS** (`query.py`) | Language filter mapping | Add `hcl`, `terraform`, `dockerfile`, `bash` entries |

## Data Flow: Detailed

### Step 1: Custom Language Definitions (New Module)

The `custom_languages` parameter is passed to the `SplitRecursively()` constructor (not at transform-call time). This means the language specs must be defined before the flow is created.

**Where it plugs in:** `SplitRecursively(custom_languages=[...])` in `flow.py`

**How the language parameter routes:** CocoIndex's `SplitRecursively` matches the `language` parameter (passed at transform time from `file["extension"]`) against both built-in Tree-sitter languages and custom language specs. When a file has extension `tf`, it does not match any built-in language (HCL is not in Tree-sitter's language pack). CocoIndex then checks `custom_languages` for a match against `language_name` or `aliases`. If found, it uses the `separators_regex` list. If not found, it falls back to plain text splitting.

**Critical insight:** The `language` parameter at transform time already receives the file extension (e.g., `"tf"`, `"sh"`). The custom language specs need `aliases` that match these extensions. Bash (`sh`) IS in Tree-sitter's built-in list but HCL (`tf`, `hcl`) and Dockerfile are NOT. For Bash, the built-in Tree-sitter chunking is likely adequate, but custom regex could provide better DevOps-specific splitting.

```python
# src/cocosearch/indexer/languages.py (NEW)

import cocoindex

# HCL/Terraform: Split at top-level block boundaries
HCL_LANGUAGE = cocoindex.functions.CustomLanguageSpec(
    language_name="hcl",
    aliases=["tf", "hcl", "tfvars"],
    separators_regex=[
        # Level 1: Top-level block boundaries (resource, data, module, etc.)
        r"\n(?=(?:resource|data|variable|output|locals|module|provider|terraform)\s)",
        # Level 2: Nested block boundaries
        r"\n(?=\s+\w+\s*\{)",
        # Level 3: Blank lines
        r"\n\n+",
        # Level 4: Single newlines
        r"\n",
    ],
)

# Dockerfile: Split at instruction boundaries
DOCKERFILE_LANGUAGE = cocoindex.functions.CustomLanguageSpec(
    language_name="dockerfile",
    aliases=["Dockerfile"],
    separators_regex=[
        # Level 1: FROM (build stage boundaries)
        r"\n(?=FROM\s)",
        # Level 2: Major instructions
        r"\n(?=(?:RUN|COPY|ADD|ENV|EXPOSE|VOLUME|WORKDIR|USER|LABEL|ARG|ENTRYPOINT|CMD|HEALTHCHECK|SHELL|ONBUILD)\s)",
        # Level 3: Blank lines / comments
        r"\n\n+",
        r"\n(?=#\s)",
        # Level 4: Single newlines
        r"\n",
    ],
)

# Bash/Shell: Split at function and major structure boundaries
BASH_LANGUAGE = cocoindex.functions.CustomLanguageSpec(
    language_name="bash",
    aliases=["sh", "bash", "zsh", "shell"],
    separators_regex=[
        # Level 1: Function definitions
        r"\n(?=\w+\s*\(\)\s*\{)",
        r"\n(?=function\s+\w+)",
        # Level 2: Major flow control
        r"\n(?=(?:if|for|while|case|until)\s)",
        # Level 3: Blank lines (logical sections)
        r"\n\n+",
        # Level 4: Comments that mark sections
        r"\n(?=#+\s)",
        # Level 5: Single newlines
        r"\n",
    ],
)

DEVOPS_CUSTOM_LANGUAGES = [HCL_LANGUAGE, DOCKERFILE_LANGUAGE, BASH_LANGUAGE]
```

**Confidence:** HIGH for the API pattern (verified from CocoIndex official docs and academic papers example). MEDIUM for the specific regex patterns (will need validation with real DevOps files during implementation).

**Important note on Bash:** Tree-sitter has a built-in `bash` language. When `custom_languages` defines a language with the same name as a built-in, the behavior needs verification. If custom definitions override builtins, the custom Bash spec above works. If builtins take priority, the custom spec would be ignored for `.sh` files. This must be tested in Phase 1.

### Step 2: Metadata Extraction (New Module)

Metadata extraction happens INSIDE the CocoIndex flow, after chunking but before embedding. This is the right place because:
- We have access to the chunk text and filename
- The metadata can be stored alongside the chunk via `collector.collect()`
- No post-processing step needed; metadata flows through the standard pipeline

**Where it plugs in:** New `@cocoindex.op.function()` called between chunking and embedding in `flow.py`

```python
# src/cocosearch/indexer/metadata.py (NEW)

import os
import re
from dataclasses import dataclass

import cocoindex


@dataclass
class DevOpsMetadata:
    """Metadata extracted from a DevOps code chunk."""
    block_type: str    # e.g., "resource", "FROM", "function"
    hierarchy: str     # e.g., "resource.aws_s3_bucket.main", "stage:build", "function:deploy"
    language_id: str   # e.g., "hcl", "dockerfile", "bash"


@cocoindex.op.function()
def extract_devops_metadata(filename: str, chunk_text: str) -> DevOpsMetadata:
    """Extract DevOps-specific metadata from a code chunk.

    Returns structured metadata about the block type, hierarchy,
    and language of the chunk.
    """
    ext = os.path.splitext(filename)[1].lstrip(".")
    basename = os.path.basename(filename)

    if ext in ("tf", "hcl", "tfvars"):
        return _extract_hcl_metadata(chunk_text)
    elif basename.startswith("Dockerfile") or basename == "Containerfile":
        return _extract_dockerfile_metadata(chunk_text)
    elif ext in ("sh", "bash", "zsh"):
        return _extract_bash_metadata(chunk_text)
    else:
        return DevOpsMetadata(block_type="", hierarchy="", language_id="")


def _extract_hcl_metadata(text: str) -> DevOpsMetadata:
    """Extract HCL block type and hierarchy."""
    # Match: resource "type" "name" {
    match = re.match(
        r'^\s*(resource|data|variable|output|locals|module|provider|terraform)'
        r'\s+"([^"]+)"(?:\s+"([^"]+)")?\s*\{',
        text, re.MULTILINE
    )
    if match:
        block_kind = match.group(1)      # resource, data, module, etc.
        type_label = match.group(2)       # aws_s3_bucket
        name_label = match.group(3) or "" # main
        hierarchy = f"{block_kind}.{type_label}"
        if name_label:
            hierarchy += f".{name_label}"
        return DevOpsMetadata(
            block_type=block_kind,
            hierarchy=hierarchy,
            language_id="hcl",
        )
    return DevOpsMetadata(block_type="block", hierarchy="", language_id="hcl")


def _extract_dockerfile_metadata(text: str) -> DevOpsMetadata:
    """Extract Dockerfile instruction type and stage context."""
    # Check for FROM with AS (build stage)
    from_match = re.match(r'^\s*FROM\s+\S+(?:\s+AS\s+(\S+))?', text, re.IGNORECASE)
    if from_match:
        stage = from_match.group(1) or "base"
        return DevOpsMetadata(
            block_type="FROM",
            hierarchy=f"stage:{stage}",
            language_id="dockerfile",
        )
    # Other instructions
    instr_match = re.match(r'^\s*(RUN|COPY|ADD|ENV|EXPOSE|VOLUME|WORKDIR|USER|LABEL|ARG|ENTRYPOINT|CMD|HEALTHCHECK|SHELL|ONBUILD)\s', text, re.IGNORECASE)
    if instr_match:
        return DevOpsMetadata(
            block_type=instr_match.group(1).upper(),
            hierarchy="",
            language_id="dockerfile",
        )
    return DevOpsMetadata(block_type="instruction", hierarchy="", language_id="dockerfile")


def _extract_bash_metadata(text: str) -> DevOpsMetadata:
    """Extract Bash function name and structure."""
    # Match: function_name() {  OR  function func_name
    func_match = re.match(r'^\s*(\w+)\s*\(\)\s*\{', text, re.MULTILINE)
    if not func_match:
        func_match = re.match(r'^\s*function\s+(\w+)', text, re.MULTILINE)
    if func_match:
        return DevOpsMetadata(
            block_type="function",
            hierarchy=f"function:{func_match.group(1)}",
            language_id="bash",
        )
    return DevOpsMetadata(block_type="script", hierarchy="", language_id="bash")
```

**Confidence:** HIGH for the approach (CocoIndex supports dataclass return types from `@cocoindex.op.function()`). MEDIUM for individual regex patterns (need validation with real files).

### Step 3: Flow Integration

The flow changes are minimal but crucial. Three modifications to `create_code_index_flow()`:

```python
# Modified flow.py (conceptual diff)

from cocosearch.indexer.languages import DEVOPS_CUSTOM_LANGUAGES
from cocosearch.indexer.metadata import extract_devops_metadata

def create_code_index_flow(...):
    @cocoindex.flow_def(name=f"CodeIndex_{index_name}")
    def code_index_flow(flow_builder, data_scope):
        # ... LocalFile source unchanged ...

        with data_scope["files"].row() as file:
            file["extension"] = file["filename"].transform(extract_extension)

            # CHANGE 1: Pass custom_languages to SplitRecursively constructor
            file["chunks"] = file["content"].transform(
                cocoindex.functions.SplitRecursively(
                    custom_languages=DEVOPS_CUSTOM_LANGUAGES,  # NEW
                ),
                language=file["extension"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            with file["chunks"].row() as chunk:
                chunk["embedding"] = chunk["text"].call(code_to_embedding)

                # CHANGE 2: Extract metadata for each chunk
                chunk["metadata"] = chunk["text"].transform(
                    extract_devops_metadata,
                    filename=file["filename"],
                )

                # CHANGE 3: Collect with metadata fields
                code_embeddings.collect(
                    filename=file["filename"],
                    location=chunk["location"],
                    embedding=chunk["embedding"],
                    block_type=chunk["metadata"]["block_type"],      # NEW
                    hierarchy=chunk["metadata"]["hierarchy"],        # NEW
                    language_id=chunk["metadata"]["language_id"],    # NEW
                )

        code_embeddings.export(
            f"{index_name}_chunks",
            cocoindex.storages.Postgres(),
            primary_key_fields=["filename", "location"],
            vector_indexes=[...],  # unchanged
        )
```

**Key design decision:** Metadata extraction runs for ALL files, not just DevOps files. For non-DevOps files, the function returns empty strings for all three fields. This avoids conditional branching in the flow (which CocoIndex does not support well) and keeps the schema consistent across all chunks.

### Step 4: Schema Changes

CocoIndex automatically creates PostgreSQL columns based on `collector.collect()` fields. Adding `block_type`, `hierarchy`, and `language_id` to the collect call creates three new TEXT columns in the chunks table.

**Current schema** (per-index table, e.g., `codeindex_myproject__myproject_chunks`):

| Column | Type | Source |
|--------|------|--------|
| `filename` | TEXT | Primary key part 1 |
| `location` | INT4RANGE | Primary key part 2 (byte range) |
| `embedding` | VECTOR(768) | Ollama nomic-embed-text |

**New schema** (v1.2):

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `filename` | TEXT | Primary key part 1 | Unchanged |
| `location` | INT4RANGE | Primary key part 2 | Unchanged |
| `embedding` | VECTOR(768) | Ollama | Unchanged |
| `block_type` | TEXT | `extract_devops_metadata` | e.g., "resource", "FROM", "function", "" for non-DevOps |
| `hierarchy` | TEXT | `extract_devops_metadata` | e.g., "resource.aws_s3_bucket.main", "" for non-DevOps |
| `language_id` | TEXT | `extract_devops_metadata` | e.g., "hcl", "dockerfile", "bash", "" for non-DevOps |

**Migration consideration:** Existing indexes will NOT have these columns. When a user re-indexes a codebase, CocoIndex's `flow.setup()` will attempt to reconcile the schema. If CocoIndex does not add columns automatically, a migration step or full re-index may be required. This needs testing.

**Alternative considered:** Store metadata as a single JSONB column instead of three TEXT columns. Rejected because: (1) TEXT columns are simpler to query with WHERE clauses, (2) individual columns can be indexed if needed, (3) the schema is stable (three known fields, not arbitrary).

### Step 5: Search Query Changes

The search SQL needs to SELECT the new columns, and `SearchResult` needs new fields.

```python
# Modified query.py (conceptual)

@dataclass
class SearchResult:
    filename: str
    start_byte: int
    end_byte: int
    score: float
    block_type: str = ""      # NEW
    hierarchy: str = ""       # NEW
    language_id: str = ""     # NEW

# SQL query adds: block_type, hierarchy, language_id to SELECT
sql = f"""
    SELECT filename, lower(location) as start_byte, upper(location) as end_byte,
           1 - (embedding <=> %s::vector) AS score,
           COALESCE(block_type, '') as block_type,
           COALESCE(hierarchy, '') as hierarchy,
           COALESCE(language_id, '') as language_id
    FROM {table_name}
    ORDER BY embedding <=> %s::vector
    LIMIT %s
"""
```

**COALESCE usage:** Handles backward compatibility with existing indexes that lack the new columns. If columns don't exist in older indexes, the query would fail -- so either we need column existence checking or accept that v1.2 requires re-indexing. The simpler approach is to require re-indexing for DevOps metadata, since semantic search still works without metadata columns on older indexes.

**Decision:** Use a try/except around the metadata-enriched query. If it fails (missing columns), fall back to the original query. This provides graceful degradation for pre-v1.2 indexes.

### Step 6: Formatter Changes

```python
# Modified format_json output
{
    "file_path": "/infra/main.tf",
    "start_line": 10,
    "end_line": 25,
    "score": 0.87,
    "content": "resource \"aws_s3_bucket\" \"data\" { ... }",
    "block_type": "resource",                          # NEW
    "hierarchy": "resource.aws_s3_bucket.data",        # NEW
    "language_id": "hcl",                              # NEW
    "context_before": [...],
    "context_after": [...]
}
```

For pretty output, metadata appears as an annotation line:

```
/infra/main.tf
  0.87 Lines 10-25  [hcl] resource.aws_s3_bucket.data
  resource "aws_s3_bucket" "data" {
    bucket = "my-data-bucket"
    ...
  }
```

Metadata is only shown when non-empty. For standard programming language files (where all metadata fields are ""), nothing extra appears -- output is identical to v1.0.

### Step 7: MCP Server Changes

The `search_code` MCP tool includes metadata in its response dicts:

```python
output.append({
    "file_path": r.filename,
    "start_line": start_line,
    "end_line": end_line,
    "score": r.score,
    "content": content,
    "block_type": r.block_type,      # NEW (empty string for non-DevOps)
    "hierarchy": r.hierarchy,        # NEW (empty string for non-DevOps)
    "language_id": r.language_id,    # NEW (empty string for non-DevOps)
})
```

No new MCP tools needed. The calling LLM (Claude) can use `block_type` and `hierarchy` to provide richer context when synthesizing answers from search results.

## Patterns to Follow

### Pattern 1: Custom Languages as Static Definitions

**What:** Define `CustomLanguageSpec` objects as module-level constants, not generated dynamically.
**When:** Always. Language specs don't change between flow runs.
**Why:** Simplifies testing (can test specs independently), avoids reconstruction on every flow creation, enables import from multiple modules.

### Pattern 2: Metadata Extraction as CocoIndex Op Function

**What:** Use `@cocoindex.op.function()` for metadata extraction, not a plain Python function.
**When:** Metadata extraction happens inside the CocoIndex flow.
**Why:** CocoIndex's op.function decorator enables caching, proper type mapping to PostgreSQL columns, and integration with the incremental processing system. A plain function would not participate in CocoIndex's dependency tracking.

### Pattern 3: Empty Strings Over Nulls for Optional Metadata

**What:** Return empty string `""` instead of `None` for chunks without metadata.
**When:** Non-DevOps files processed through the same pipeline.
**Why:** Avoids NULL handling complexity in SQL queries and downstream formatters. `WHERE block_type != ''` is cleaner than `WHERE block_type IS NOT NULL AND block_type != ''`. Consistent with the existing pattern of using empty strings (e.g., `extract_extension` returns `""` for files without extensions).

### Pattern 4: Graceful Degradation for Pre-v1.2 Indexes

**What:** Search queries fall back to the v1.0 column set if metadata columns don't exist.
**When:** Querying indexes created before v1.2.
**Why:** Users should not be forced to re-index all codebases immediately after upgrading.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Post-Processing Metadata Outside the Flow

**What people do:** Run a separate pass after indexing to extract metadata and UPDATE rows.
**Why it's wrong:** Breaks CocoIndex's incremental processing model. The second pass would need to track which chunks changed independently. Doubles write operations. Creates a window where chunks exist without metadata.
**Do this instead:** Extract metadata inside the flow, before the collector, so metadata is stored atomically with each chunk.

### Anti-Pattern 2: Conditional Flow Branching by Language

**What people do:** Create separate flow paths for DevOps vs. programming language files.
**Why it's wrong:** CocoIndex flows are declarative data pipelines, not imperative programs. Conditional branching (if file is HCL, do X, else do Y) is not well-supported. Maintaining two paths doubles complexity and testing burden.
**Do this instead:** Run the same pipeline for all files. The `extract_devops_metadata` function returns empty metadata for non-DevOps files. The `custom_languages` parameter gracefully falls back to built-in Tree-sitter or plain text for unsupported extensions.

### Anti-Pattern 3: Storing Metadata as JSONB Blob

**What people do:** Pack all metadata into a single `metadata JSONB` column.
**Why it's wrong:** Harder to query (`WHERE metadata->>'block_type' = 'resource'` vs. `WHERE block_type = 'resource'`), can't add standard indexes, CocoIndex's type system handles struct fields as individual columns naturally.
**Do this instead:** Use individual typed columns. CocoIndex maps dataclass fields to separate PostgreSQL columns automatically.

### Anti-Pattern 4: Overriding Built-in Tree-sitter with Custom Regex

**What people do:** Define custom regex for languages that Tree-sitter already handles (e.g., Python, JavaScript).
**Why it's wrong:** Tree-sitter parses actual ASTs and produces semantically meaningful boundaries. Regex approximations are always inferior for languages with complex syntax.
**Do this instead:** Only use `custom_languages` for languages NOT in Tree-sitter's language pack. For Bash: test whether Tree-sitter's built-in bash support is adequate before adding a custom spec.

## Decision: Metadata Extraction Inside vs. Outside the Flow

| Approach | Inside Flow | Outside Flow (Post-Processing) |
|----------|-------------|-------------------------------|
| **Incremental support** | Automatic (CocoIndex tracks) | Must implement separately |
| **Atomicity** | Chunk + metadata stored together | Window without metadata |
| **Complexity** | Single pipeline | Two-pass system |
| **Performance** | One pass over files | Two passes |
| **Flexibility** | Limited to CocoIndex ops | Any Python code |
| **Testing** | Test as CocoIndex op | Test independently |

**Decision:** Inside the flow. The incremental processing benefit alone justifies this. When a file changes, CocoIndex re-processes only that file's chunks, and metadata is automatically updated along with the new chunks.

## Decision: Separate Flow vs. Single Flow with Custom Languages

| Approach | Single Flow + custom_languages | Separate DevOps Flow |
|----------|-------------------------------|---------------------|
| **Index management** | One index per codebase | Two indexes per codebase |
| **Search** | Single query searches all files | Must query two indexes and merge |
| **Complexity** | Lower (extend existing flow) | Higher (new flow, merge logic) |
| **Schema** | Unified with optional metadata | Clean separation |
| **User experience** | Transparent (same commands) | New flags/options needed |

**Decision:** Single flow with `custom_languages`. Users should not need to manage separate indexes for DevOps files. A mixed codebase (Python + Terraform) should be searchable from a single index. The metadata columns being empty for non-DevOps files is a small cost for much simpler UX.

## Build Order Dependencies

```
Phase 1: Custom Language Definitions
|  - Define CustomLanguageSpec for HCL, Dockerfile, Bash
|  - Verify custom_languages parameter works with SplitRecursively
|  - Test: Bash override behavior (custom vs. Tree-sitter built-in)
|  - Test: Extension-to-language routing (tf -> hcl, Dockerfile -> dockerfile)
|  No dependencies.
|
Phase 2: Metadata Extraction
|  - Create extract_devops_metadata op function
|  - Implement HCL, Dockerfile, Bash extractors
|  - Test: regex patterns against real DevOps files
|  Depends on: Phase 1 (need to know chunk boundaries to test extraction)
|
Phase 3: Flow Integration + Schema
|  - Modify create_code_index_flow to add custom_languages
|  - Add metadata extraction step
|  - Add metadata fields to collector
|  - Update IndexingConfig with DevOps file patterns
|  - Test: End-to-end indexing of DevOps files
|  Depends on: Phase 1 + Phase 2
|
Phase 4: Search + Output Integration
|  - Extend SearchResult with metadata fields
|  - Update SQL queries to include metadata columns
|  - Implement graceful degradation for pre-v1.2 indexes
|  - Update format_json and format_pretty
|  - Update MCP server search_code response
|  - Update LANGUAGE_EXTENSIONS mapping
|  - Test: Search results include metadata
|  Depends on: Phase 3 (needs populated metadata in DB)
```

**Critical path:** Language definitions -> Flow integration -> Search integration

**Parallelizable:** Metadata extraction development can start in parallel with language definition testing, since the extraction function is unit-testable without a running CocoIndex flow.

## New File Structure

```
src/cocosearch/
    indexer/
        __init__.py          # Add new module exports
        config.py            # MODIFY: Add DevOps file patterns
        embedder.py          # UNCHANGED
        file_filter.py       # UNCHANGED
        flow.py              # MODIFY: Add custom_languages + metadata extraction
        languages.py         # NEW: CustomLanguageSpec definitions
        metadata.py          # NEW: extract_devops_metadata function
        progress.py          # UNCHANGED
    search/
        __init__.py          # Update exports if needed
        db.py                # UNCHANGED
        formatter.py         # MODIFY: Include metadata in output
        query.py             # MODIFY: SearchResult fields + SQL columns + language mapping
        repl.py              # UNCHANGED (calls search, gets metadata automatically)
        utils.py             # UNCHANGED
    management/             # UNCHANGED
    mcp/
        server.py            # MODIFY: Include metadata in search_code response
    cli.py                   # MINOR: DevOps language filter support
```

**Total new files:** 2 (`languages.py`, `metadata.py`)
**Total modified files:** 5 (`config.py`, `flow.py`, `query.py`, `formatter.py`, `server.py`)
**Modified with minor changes:** 1 (`cli.py`)

## Scalability Considerations

| Concern | Impact | Mitigation |
|---------|--------|------------|
| Metadata columns increase row size | ~100-200 bytes per row (3 TEXT fields, mostly short strings) | Negligible vs. 768-dim vector (~3KB) |
| Metadata extraction adds processing time | Regex matching is sub-millisecond per chunk | No measurable impact |
| Custom language regex for large files | Regex separators are O(n) per file | Same as built-in, acceptable |
| Schema migration for existing indexes | Requires re-index | One-time cost, documented |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `custom_languages` conflicts with built-in Bash | MEDIUM | Needs workaround | Test early in Phase 1; if conflict, rename custom spec |
| CocoIndex dataclass return from op.function doesn't map to separate columns | LOW | Must restructure | Verified in docs; academic papers example uses structured returns |
| Regex patterns don't capture all HCL/Dockerfile variants | MEDIUM | Incomplete metadata | Start with common patterns, iterate; empty metadata is safe fallback |
| Existing index schema incompatible with new columns | HIGH | Must re-index | Implement graceful degradation; document re-index requirement |
| `extract_devops_metadata` perf on large repos | LOW | Slower indexing | Regex is fast; only meaningful if >100K files |

## Sources

- [CocoIndex Functions Documentation](https://cocoindex.io/docs/ops/functions) -- `SplitRecursively` API, `CustomLanguageSpec` structure [HIGH confidence]
- [CocoIndex Academic Papers Example](https://cocoindex.io/docs/examples/academic_papers_index) -- `CustomLanguageSpec` usage with `SplitRecursively` constructor [HIGH confidence]
- [CocoIndex Custom Functions](https://cocoindex.io/docs/custom_ops/custom_functions) -- `@cocoindex.op.function()` decorator, return type annotations [HIGH confidence]
- [CocoIndex Data Types](https://cocoindex.io/docs/core/data_types) -- Struct/dataclass return types supported [HIGH confidence]
- [CocoIndex Real-time Codebase Indexing Example](https://cocoindex.io/docs/examples/code_index) -- Existing flow pattern [HIGH confidence]
- [Terraform Syntax Documentation](https://developer.hashicorp.com/terraform/language/syntax/configuration) -- HCL block structure [HIGH confidence]
- [Dockerfile Reference](https://docs.docker.com/reference/dockerfile/) -- Instruction structure [HIGH confidence]
- CocoSearch source code analysis (flow.py, query.py, formatter.py, server.py, config.py) -- Integration points [HIGH confidence, direct code reading]

---
*Architecture research for: CocoSearch v1.2 DevOps Language Support*
*Researched: 2026-01-27*
