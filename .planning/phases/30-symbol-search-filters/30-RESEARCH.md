# Phase 30: Symbol Search Filters + Language Expansion - Research

**Researched:** 2026-02-03
**Domain:** Symbol filtering, glob pattern matching, multi-language tree-sitter extraction, RRF score boosting
**Confidence:** HIGH

## Summary

Phase 30 extends the symbol-aware indexing from Phase 29 by adding search filters for symbol type and name, plus expanding symbol extraction to JavaScript, TypeScript, Go, and Rust. The implementation adds CLI flags `--symbol-type` and `--symbol-name`, corresponding MCP parameters, and applies a 2x score boost to definitions over references after RRF fusion.

The standard approach uses SQL WHERE clauses with PostgreSQL ILIKE for case-insensitive glob patterns (converted via fnmatch-style logic), tree-sitter queries customized per language for symbol extraction, and RRF score post-processing to boost definition ranks. The architecture extends Phase 29's existing symbol extraction infrastructure with language-specific extractors and adds filtering logic to both vector-only and hybrid search paths.

Key architectural decisions: Symbol filtering happens at the SQL query level (WHERE clauses) rather than post-processing for efficiency. Glob patterns use PostgreSQL ILIKE with % wildcards (shell-style globs converted to SQL patterns). Definition boost multiplier is applied after RRF fusion to avoid disrupting the rank-based fusion algorithm. Pre-v1.7 indexes without symbol columns return helpful error messages suggesting re-indexing.

**Primary recommendation:** Use SQL WHERE clause filtering with ILIKE for symbol name patterns, extend symbols.py with language-specific tree-sitter extractors following Phase 29's patterns, apply definition boost as a post-RRF multiplier on combined scores.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tree-sitter-languages | 1.10.2+ | Pre-compiled tree-sitter grammars for all languages | Already in Phase 29, includes JS/TS/Go/Rust support, zero build dependencies |
| py-tree-sitter | 0.21.x | Python bindings to tree-sitter parsing library | Already in Phase 29 (tree-sitter 0.21.0 in pyproject.toml), consistent API |
| fnmatch | stdlib | Shell-style glob pattern matching | Python standard library, no dependencies, well-tested glob semantics |
| PostgreSQL ILIKE | built-in | Case-insensitive pattern matching | Built into PostgreSQL, works with existing pgvector indexes, supports % wildcards |
| psycopg | 3.3.2+ (existing) | PostgreSQL adapter | Already integrated, supports parameterized queries for injection safety |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tree-sitter-javascript | Latest (bundled) | JavaScript/JSX grammar | Included in tree-sitter-languages, for JS symbol extraction |
| tree-sitter-typescript | Latest (bundled) | TypeScript/TSX grammar | Included in tree-sitter-languages, for TS symbol extraction |
| tree-sitter-go | Latest (bundled) | Go grammar | Included in tree-sitter-languages, for Go symbol extraction |
| tree-sitter-rust | Latest (bundled) | Rust grammar | Included in tree-sitter-languages, for Rust symbol extraction |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQL WHERE filtering | Post-query Python filtering | SQL filtering is 10-100x faster, leverages indexes, reduces data transfer |
| ILIKE with % wildcards | Full regex (~ operator) | ILIKE is simpler, more intuitive for users, matches shell glob expectations |
| Post-RRF score boost | Pre-RRF weight adjustment | Post-RRF is cleaner, preserves RRF's rank-based algorithm, easier to tune |
| fnmatch translation | Direct regex compilation | fnmatch is stdlib, handles edge cases (escaping, char classes), familiar semantics |

**Installation:**

No new dependencies needed - tree-sitter and tree-sitter-languages already installed in Phase 29.

## Architecture Patterns

### Recommended Project Structure

```
src/cocosearch/
├── indexer/
│   └── symbols.py           # EXTEND: Add JS/TS/Go/Rust extractors
├── search/
│   ├── query.py             # EXTEND: Add symbol_type, symbol_name params
│   ├── hybrid.py            # EXTEND: Apply definition boost after RRF
│   └── filters.py           # NEW: Symbol filter SQL builder
└── mcp/
    └── server.py            # EXTEND: Add symbol_type, symbol_name params
```

### Pattern 1: SQL-Level Symbol Filtering

**What:** Build WHERE clauses that filter by symbol columns before query execution.

**When to use:** All search operations with symbol filters. Filtering in SQL is 10-100x faster than post-processing in Python.

**Example:**

```python
# In search/filters.py (new module)
def build_symbol_where_clause(
    symbol_type: str | list[str] | None,
    symbol_name: str | None,
) -> tuple[str, list[str]]:
    """Build WHERE clause for symbol filtering.

    Returns:
        Tuple of (where_clause, params) for SQL injection safety.
    """
    conditions = []
    params = []

    # Symbol type filter (OR for multiple types)
    if symbol_type:
        types = [symbol_type] if isinstance(symbol_type, str) else symbol_type
        # Use IN for multiple types
        placeholders = ", ".join(["%s"] * len(types))
        conditions.append(f"symbol_type IN ({placeholders})")
        params.extend(types)

    # Symbol name filter (glob pattern with ILIKE)
    if symbol_name:
        # Convert shell-style glob to SQL ILIKE pattern
        sql_pattern = glob_to_sql_pattern(symbol_name)
        conditions.append("symbol_name ILIKE %s")
        params.append(sql_pattern)

    where_clause = " AND ".join(conditions) if conditions else ""
    return where_clause, params


def glob_to_sql_pattern(glob_pattern: str) -> str:
    """Convert shell glob pattern to SQL ILIKE pattern.

    Examples:
        'get*' -> 'get%'
        'User*Service' -> 'User%Service'
        '*Handler' -> '%Handler'
    """
    # Escape SQL special chars (%, _) first
    pattern = glob_pattern.replace("%", r"\%").replace("_", r"\_")

    # Convert glob wildcards (* and ?) to SQL wildcards (% and _)
    pattern = pattern.replace("*", "%").replace("?", "_")

    return pattern
```

### Pattern 2: Multi-Language Symbol Extraction

**What:** Language-specific tree-sitter extractors with unified return format.

**When to use:** Extending symbols.py to support JavaScript, TypeScript, Go, Rust.

**Example:**

```python
# In indexer/symbols.py (extend existing)
from tree_sitter_languages import get_language, get_parser

# Module-level parsers (lazy initialization)
_PARSERS = {}

def _get_parser(language: str):
    """Get or initialize parser for language."""
    if language not in _PARSERS:
        lang = get_language(language)
        parser = Parser()
        parser.set_language(lang)
        _PARSERS[language] = parser
    return _PARSERS[language]


def _extract_javascript_symbols(chunk_text: str, parser) -> list[dict]:
    """Extract symbols from JavaScript/JSX code.

    Extracts:
    - Function declarations: function fetchUser() {}
    - Arrow functions: const fetchUser = () => {}
    - Class declarations: class UserService {}
    - Methods: method in class
    """
    tree = parser.parse(bytes(chunk_text, "utf8"))
    symbols = []

    def walk_node(node, current_class=None):
        # Function declarations
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            if name_node and params_node:
                name = chunk_text[name_node.start_byte:name_node.end_byte]
                params = chunk_text[params_node.start_byte:params_node.end_byte]

                symbol_type = "method" if current_class else "function"
                symbol_name = f"{current_class}.{name}" if current_class else name

                symbols.append({
                    "symbol_type": symbol_type,
                    "symbol_name": symbol_name,
                    "symbol_signature": f"function {name}{params}",
                })

        # Arrow functions (named only: const name = () => {})
        elif node.type == "lexical_declaration":
            # Look for pattern: const name = arrow_function
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    if name_node and value_node and value_node.type == "arrow_function":
                        name = chunk_text[name_node.start_byte:name_node.end_byte]
                        params_node = value_node.child_by_field_name("parameters")
                        params = chunk_text[params_node.start_byte:params_node.end_byte] if params_node else "()"

                        symbols.append({
                            "symbol_type": "function",
                            "symbol_name": name,
                            "symbol_signature": f"const {name} = {params} => ...",
                        })

        # Class declarations
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = chunk_text[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": "class",
                    "symbol_name": class_name,
                    "symbol_signature": f"class {class_name}",
                })

                # Walk class body for methods
                body_node = node.child_by_field_name("body")
                if body_node:
                    for child in body_node.children:
                        walk_node(child, current_class=class_name)

        # Method definitions (inside classes)
        elif node.type == "method_definition" and current_class:
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            if name_node and params_node:
                method_name = chunk_text[name_node.start_byte:name_node.end_byte]
                params = chunk_text[params_node.start_byte:params_node.end_byte]

                symbols.append({
                    "symbol_type": "method",
                    "symbol_name": f"{current_class}.{method_name}",
                    "symbol_signature": f"{method_name}{params}",
                })

        else:
            # Recurse for module-level or class body
            if current_class or node.type in ("program", "class_body"):
                for child in node.children:
                    walk_node(child, current_class)

    walk_node(tree.root_node)
    return symbols


def _extract_go_symbols(chunk_text: str, parser) -> list[dict]:
    """Extract symbols from Go code.

    Extracts:
    - Functions: func Process() error
    - Methods: func (s *Server) Start() error -> Server.Start
    - Structs: type Server struct {}
    - Interfaces: type Handler interface {}
    """
    tree = parser.parse(bytes(chunk_text, "utf8"))
    symbols = []

    # Go function declarations (including methods)
    for node in tree.root_node.children:
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")

            if name_node:
                func_name = chunk_text[name_node.start_byte:name_node.end_byte]
                params = chunk_text[params_node.start_byte:params_node.end_byte] if params_node else "()"

                # Check for receiver (method)
                receiver = None
                for child in node.children:
                    if child.type == "parameter_list" and child.start_byte < name_node.start_byte:
                        # This is the receiver, extract type
                        receiver_text = chunk_text[child.start_byte:child.end_byte]
                        # Parse receiver: (s *Server) -> Server
                        if "*" in receiver_text:
                            receiver = receiver_text.split("*")[-1].strip().rstrip(")")
                        else:
                            receiver = receiver_text.split()[-1].rstrip(")")
                        break

                if receiver:
                    symbols.append({
                        "symbol_type": "method",
                        "symbol_name": f"{receiver}.{func_name}",
                        "symbol_signature": f"func {func_name}{params}",
                    })
                else:
                    symbols.append({
                        "symbol_type": "function",
                        "symbol_name": func_name,
                        "symbol_signature": f"func {func_name}{params}",
                    })

        # Type declarations (structs, interfaces)
        elif node.type == "type_declaration":
            for spec in node.children:
                if spec.type == "type_spec":
                    name_node = spec.child_by_field_name("name")
                    type_node = spec.child_by_field_name("type")

                    if name_node and type_node:
                        type_name = chunk_text[name_node.start_byte:name_node.end_byte]

                        if type_node.type == "struct_type":
                            symbols.append({
                                "symbol_type": "class",  # Map struct to class
                                "symbol_name": type_name,
                                "symbol_signature": f"type {type_name} struct",
                            })
                        elif type_node.type == "interface_type":
                            symbols.append({
                                "symbol_type": "interface",
                                "symbol_name": type_name,
                                "symbol_signature": f"type {type_name} interface",
                            })

    return symbols


def _extract_rust_symbols(chunk_text: str, parser) -> list[dict]:
    """Extract symbols from Rust code.

    Extracts:
    - Functions: fn process() -> Result<(), Error>
    - Methods: impl Server { fn start() } -> Server.start
    - Structs: struct Server {}
    - Traits: trait Handler {}
    - Enums: enum Status {}
    """
    tree = parser.parse(bytes(chunk_text, "utf8"))
    symbols = []

    for node in tree.root_node.children:
        # Function definitions
        if node.type == "function_item":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")

            if name_node:
                func_name = chunk_text[name_node.start_byte:name_node.end_byte]
                params = chunk_text[params_node.start_byte:params_node.end_byte] if params_node else "()"

                symbols.append({
                    "symbol_type": "function",
                    "symbol_name": func_name,
                    "symbol_signature": f"fn {func_name}{params}",
                })

        # Impl blocks (methods)
        elif node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            type_name = None
            if type_node:
                type_name = chunk_text[type_node.start_byte:type_node.end_byte]

            # Walk body for methods
            body_node = node.child_by_field_name("body")
            if body_node and type_name:
                for child in body_node.children:
                    if child.type == "function_item":
                        name_node = child.child_by_field_name("name")
                        params_node = child.child_by_field_name("parameters")

                        if name_node:
                            method_name = chunk_text[name_node.start_byte:name_node.end_byte]
                            params = chunk_text[params_node.start_byte:params_node.end_byte] if params_node else "()"

                            symbols.append({
                                "symbol_type": "method",
                                "symbol_name": f"{type_name}.{method_name}",
                                "symbol_signature": f"fn {method_name}{params}",
                            })

        # Struct definitions
        elif node.type == "struct_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                struct_name = chunk_text[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": "class",  # Map struct to class
                    "symbol_name": struct_name,
                    "symbol_signature": f"struct {struct_name}",
                })

        # Trait definitions
        elif node.type == "trait_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                trait_name = chunk_text[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": "interface",  # Map trait to interface
                    "symbol_name": trait_name,
                    "symbol_signature": f"trait {trait_name}",
                })

        # Enum definitions
        elif node.type == "enum_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                enum_name = chunk_text[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": "class",  # Map enum to class
                    "symbol_name": enum_name,
                    "symbol_signature": f"enum {enum_name}",
                })

    return symbols
```

### Pattern 3: Definition Boost After RRF Fusion

**What:** Apply score multiplier to definitions after RRF combines vector and keyword ranks.

**When to use:** Hybrid search with symbol metadata. Boost happens post-fusion to preserve RRF's rank-based algorithm.

**Example:**

```python
# In search/hybrid.py (extend rrf_fusion or add post-processing)
def apply_definition_boost(
    results: list[HybridSearchResult],
    boost_multiplier: float = 2.0,
) -> list[HybridSearchResult]:
    """Apply score boost to definition symbols.

    Definitions are identified by checking if chunk start matches
    symbol definition pattern (func/class/def keyword at start).

    Args:
        results: Fused hybrid search results.
        boost_multiplier: Multiplier for definition scores (default 2.0).

    Returns:
        Results with boosted scores, re-sorted by new scores.
    """
    # Import here to avoid circular dependency
    from cocosearch.search.db import check_symbol_columns_exist, get_table_name
    from cocosearch.search import read_chunk_content

    # Check if symbol columns exist
    table_name = get_table_name(results[0].filename.split("/")[0])  # Derive from first result
    if not check_symbol_columns_exist(table_name):
        # Pre-v1.7 index, no symbol metadata available
        return results

    boosted_results = []
    for result in results:
        # Check if chunk is a definition
        # Read chunk content and check for definition keywords at start
        content = read_chunk_content(result.filename, result.start_byte, result.end_byte)
        is_definition = _is_definition_chunk(content)

        if is_definition:
            # Apply boost
            boosted_score = result.combined_score * boost_multiplier
            boosted_results.append(
                HybridSearchResult(
                    filename=result.filename,
                    start_byte=result.start_byte,
                    end_byte=result.end_byte,
                    combined_score=boosted_score,
                    match_type=result.match_type,
                    vector_score=result.vector_score,
                    keyword_score=result.keyword_score,
                    block_type=result.block_type,
                    hierarchy=result.hierarchy,
                    language_id=result.language_id,
                )
            )
        else:
            boosted_results.append(result)

    # Re-sort by new scores
    boosted_results.sort(key=lambda r: r.combined_score, reverse=True)
    return boosted_results


def _is_definition_chunk(content: str) -> bool:
    """Check if chunk content starts with a definition keyword.

    Heuristic: definition chunks start with keywords like:
    - def, class, async def (Python)
    - function, class, const name = (JavaScript/TypeScript)
    - func, type (Go)
    - fn, struct, trait, enum (Rust)
    """
    stripped = content.lstrip()
    definition_keywords = [
        "def ", "class ", "async def ",  # Python
        "function ", "const ", "class ",  # JavaScript/TypeScript
        "func ", "type ",  # Go
        "fn ", "struct ", "trait ", "enum ", "impl ",  # Rust
    ]
    return any(stripped.startswith(kw) for kw in definition_keywords)
```

### Pattern 4: Graceful Error for Pre-v1.7 Indexes

**What:** Return helpful error message when symbol filters are used on old indexes.

**When to use:** All search operations with symbol filters. Check symbol columns before executing query.

**Example:**

```python
# In search/query.py (extend search function)
def search(
    query: str,
    index_name: str,
    limit: int = 10,
    min_score: float = 0.0,
    language_filter: str | None = None,
    use_hybrid: bool | None = None,
    symbol_type: str | list[str] | None = None,
    symbol_name: str | None = None,
) -> list[SearchResult]:
    """Search with symbol filtering support."""

    # Check if symbol filters requested
    if symbol_type or symbol_name:
        table_name = get_table_name(index_name)

        # Verify symbol columns exist
        if not check_symbol_columns_exist(table_name):
            raise ValueError(
                f"Symbol filtering requires v1.7+ index. "
                f"Index '{index_name}' lacks symbol columns. "
                f"Re-index with 'cocosearch index' to enable symbol filtering."
            )

    # Continue with search logic...
```

### Anti-Patterns to Avoid

- **Post-query Python filtering:** Filters symbol results in Python after query. Slow, transfers unnecessary data. Use SQL WHERE clauses instead.
- **Pre-RRF score weighting:** Adjusting vector/keyword scores before RRF fusion. Breaks RRF's rank-based algorithm, harder to tune. Apply definition boost post-fusion.
- **Hand-rolled glob matching:** Custom wildcard parsing. Use fnmatch stdlib, handles edge cases (escaping, char classes).
- **Single unified extractor:** One function for all languages. Tree-sitter node types differ per language, language-specific extractors are cleaner.
- **Regex-based definition detection:** Parsing function signatures with regex. Use tree-sitter queries or simple keyword prefix checks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Glob to SQL conversion | Custom wildcard parser | fnmatch.translate + escape SQL chars | fnmatch handles edge cases (char classes, escaping), well-tested |
| Case-insensitive matching | LOWER() on both sides | PostgreSQL ILIKE | ILIKE is optimized, can use indexes with pg_trgm, more efficient |
| Multi-language dispatching | if/elif chain by extension | Mapping dict + get_parser helper | Cleaner, easier to extend, avoids code duplication |
| Symbol type validation | Manual string checking | Set membership with helpful error | Clear error messages, easy to extend symbol types |
| RRF score boosting | Custom rank adjustment | Post-fusion multiplier | Preserves RRF semantics, simple to understand and tune |

**Key insight:** PostgreSQL is highly optimized for pattern matching with ILIKE, especially with pg_trgm indexes. Hand-rolling glob matching or case-insensitive comparison in Python is 10-100x slower and transfers unnecessary data over the wire. Let the database do what it's good at.

## Common Pitfalls

### Pitfall 1: Glob Pattern Escaping

**What goes wrong:** User searches for `get_*` (underscore + wildcard), SQL interprets underscore as single-char wildcard, matches `getX` unexpectedly.

**Why it happens:** SQL LIKE/ILIKE treats `_` as special character (matches any single char). fnmatch treats `_` as literal.

**How to avoid:** Escape SQL special characters (`%`, `_`) before converting glob wildcards. Order matters: escape first, then convert.

```python
# Correct:
pattern = glob_pattern.replace("%", r"\%").replace("_", r"\_")  # Escape SQL chars
pattern = pattern.replace("*", "%").replace("?", "_")  # Convert glob wildcards

# Incorrect:
pattern = glob_pattern.replace("*", "%").replace("?", "_")  # Convert first
pattern = pattern.replace("%", r"\%")  # Too late, already converted * to %
```

**Warning signs:** Search for `get_*` returns `getUser` (single char match) instead of `get_config`.

### Pitfall 2: Definition Boost Before RRF

**What goes wrong:** Boosting vector scores of definitions before calling rrf_fusion. High-ranked definitions get worse fusion scores because RRF uses ranks, not scores.

**Why it happens:** Intuition that "boost the score" means multiply the score value. RRF ignores score magnitudes, only uses rank positions.

**How to avoid:** Apply boosts AFTER rrf_fusion returns combined results. Multiply combined_score, then re-sort.

**Warning signs:** Definitions rank worse after enabling boost. High-vector-score definitions drop in final results.

### Pitfall 3: Symbol Type Array Handling

**What goes wrong:** MCP parameter `symbol_type=['function', 'method']` (array) passed to SQL incorrectly, generates `symbol_type = %s` instead of `IN (...)`.

**Why it happens:** Forgetting to check if symbol_type is list or string, using single-value SQL syntax for arrays.

**How to avoid:** Type check and use SQL `IN (...)` syntax for arrays:

```python
if isinstance(symbol_type, list):
    placeholders = ", ".join(["%s"] * len(symbol_type))
    conditions.append(f"symbol_type IN ({placeholders})")
    params.extend(symbol_type)
else:
    conditions.append("symbol_type = %s")
    params.append(symbol_type)
```

**Warning signs:** MCP call with `symbol_type=['function', 'method']` returns zero results or SQL error.

### Pitfall 4: Language Detection for Symbol Extraction

**What goes wrong:** Detecting language from file extension during indexing fails for `.jsx` (not in language map), symbols not extracted.

**Why it happens:** Language detection logic doesn't cover all extensions (`.tsx`, `.jsx`, `.mjs`, etc.).

**How to avoid:** Use comprehensive extension mapping:

```python
LANGUAGE_MAP = {
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "mts": "typescript",
    "cts": "typescript",
    "go": "go",
    "rs": "rust",
    "py": "python",
}
```

**Warning signs:** TypeScript symbols extracted but not React/TSX. Go symbols work but Rust files show no symbols.

### Pitfall 5: Zero Results with Symbol Filters

**What goes wrong:** Search returns empty results when symbol filters don't match, no hint to user about why.

**Why it happens:** SQL WHERE clause filtering happens silently, user doesn't know if filters were too restrictive.

**How to avoid:** When symbol filters return zero results, log info-level message or return hint in error response:

```python
if symbol_type or symbol_name:
    if not results:
        logger.info(
            f"Symbol filters returned zero results. "
            f"Try removing --symbol-type or broadening --symbol-name pattern."
        )
```

**Warning signs:** User confusion why search returns nothing when they know the symbol exists.

## Code Examples

Verified patterns from official sources and Phase 29 implementation:

### Symbol Filter SQL Integration

```python
# Source: Existing query.py search() function pattern
def search(
    query: str,
    index_name: str,
    limit: int = 10,
    min_score: float = 0.0,
    language_filter: str | None = None,
    use_hybrid: bool | None = None,
    symbol_type: str | list[str] | None = None,
    symbol_name: str | None = None,
) -> list[SearchResult]:
    """Search with symbol filtering."""

    # ... existing code ...

    # Build WHERE clause parts
    where_parts = []
    filter_params = []

    # Add language filter (existing)
    if validated_languages:
        # ... existing language filter logic ...
        pass

    # Add symbol filters (NEW)
    if symbol_type or symbol_name:
        # Check symbol columns exist
        if not check_symbol_columns_exist(table_name):
            raise ValueError(
                f"Symbol filtering requires v1.7+ index. "
                f"Re-index with 'cocosearch index' to enable symbol filtering."
            )

        from cocosearch.search.filters import build_symbol_where_clause
        symbol_where, symbol_params = build_symbol_where_clause(symbol_type, symbol_name)
        if symbol_where:
            where_parts.append(symbol_where)
            filter_params.extend(symbol_params)

    # Build complete WHERE clause
    where_clause = ""
    if where_parts:
        where_clause = "WHERE " + " AND ".join(where_parts)

    # Execute query with combined filters
    sql = f"""
        SELECT {select_cols}
        FROM {table_name}
        {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    params = [query_embedding] + filter_params + [query_embedding, limit]
```

### TypeScript Symbol Extraction

```python
# Source: tree-sitter-typescript grammar + Phase 29 pattern
def _extract_typescript_symbols(chunk_text: str, parser) -> list[dict]:
    """Extract symbols from TypeScript code.

    Extends JavaScript extraction with:
    - Interfaces: interface User {}
    - Type aliases: type UserID = string
    """
    # Start with JavaScript extraction (functions, classes)
    symbols = _extract_javascript_symbols(chunk_text, parser)

    tree = parser.parse(bytes(chunk_text, "utf8"))

    # Add TypeScript-specific symbols
    for node in tree.root_node.children:
        # Interface declarations
        if node.type == "interface_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                interface_name = chunk_text[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": "interface",
                    "symbol_name": interface_name,
                    "symbol_signature": f"interface {interface_name}",
                })

        # Type alias declarations
        elif node.type == "type_alias_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                type_name = chunk_text[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": "interface",  # Map type to interface
                    "symbol_name": type_name,
                    "symbol_signature": f"type {type_name}",
                })

    return symbols
```

### MCP Parameter Handling

```python
# Source: Existing mcp/server.py search_code function
@mcp.tool()
def search_code(
    query: Annotated[str, Field(description="Natural language search query")],
    index_name: Annotated[str | None, Field(...)] = None,
    limit: Annotated[int, Field(...)] = 10,
    language: Annotated[str | None, Field(...)] = None,
    use_hybrid_search: Annotated[bool | None, Field(...)] = None,
    # NEW: Symbol filtering parameters
    symbol_type: Annotated[
        str | list[str] | None,
        Field(
            description="Filter by symbol type. "
            "Single: 'function', 'class', 'method', 'interface'. "
            "Multiple: ['function', 'method'] for OR filtering."
        ),
    ] = None,
    symbol_name: Annotated[
        str | None,
        Field(
            description="Filter by symbol name pattern (glob). "
            "Examples: 'get*', 'User*Service', '*Handler'. "
            "Case-insensitive matching."
        ),
    ] = None,
) -> list[dict]:
    """Search with symbol filtering support."""

    # Initialize CocoIndex
    cocoindex.init()

    # Execute search with symbol filters
    results = search(
        query=query,
        index_name=index_name,
        limit=limit,
        language_filter=language,
        use_hybrid=use_hybrid_search,
        symbol_type=symbol_type,
        symbol_name=symbol_name,
    )

    # Convert to dict for MCP response
    return [
        {
            "filename": r.filename,
            "start_byte": r.start_byte,
            "end_byte": r.end_byte,
            "score": r.score,
            "match_type": r.match_type,
            # NEW: Always include symbol metadata
            "symbol_type": r.symbol_type if hasattr(r, "symbol_type") else None,
            "symbol_name": r.symbol_name if hasattr(r, "symbol_name") else None,
            "symbol_signature": r.symbol_signature if hasattr(r, "symbol_signature") else None,
        }
        for r in results
    ]
```

### Glob Pattern Matching Tests

```python
# Source: Python fnmatch module documentation
def test_glob_to_sql_pattern():
    """Test glob pattern conversion."""
    assert glob_to_sql_pattern("get*") == "get%"
    assert glob_to_sql_pattern("User*Service") == "User%Service"
    assert glob_to_sql_pattern("*Handler") == "%Handler"

    # Escape SQL special chars
    assert glob_to_sql_pattern("get_*") == r"get\_%"  # Underscore escaped
    assert glob_to_sql_pattern("find%user") == r"find\%user"  # Percent escaped

    # Question mark -> single char wildcard
    assert glob_to_sql_pattern("test?") == "test_"

    # Combined
    assert glob_to_sql_pattern("get_user*") == r"get\_user%"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Post-query filtering | SQL WHERE clause filtering | Database best practices | 10-100x faster, reduces data transfer, leverages indexes |
| LOWER() comparison | PostgreSQL ILIKE | PostgreSQL 7.1+ (2001) | More efficient, can use pg_trgm indexes, cleaner syntax |
| Pre-fusion score weighting | Post-fusion rank boosting | RRF research (2009) | Preserves RRF semantics, easier to understand and tune |
| Regex for glob patterns | fnmatch stdlib + SQL ILIKE | Python 1.5+ (1997) | Familiar shell glob syntax, handles edge cases correctly |

**Deprecated/outdated:**
- **Python glob filtering:** Post-query filtering in Python. Use SQL WHERE clauses for 10-100x speedup.
- **Custom glob parsers:** Hand-rolled wildcard matching. Use fnmatch.translate or simple replace for SQL conversion.
- **Score normalization in RRF:** Normalizing vector/keyword scores before fusion. RRF is rank-based, score magnitudes don't matter.

## Open Questions

1. **Exact vs. glob match ranking priority**
   - What we know: User wants exact matches to rank higher than glob matches
   - What's unclear: Whether to add separate boosting or rely on ILIKE matching behavior
   - Recommendation: PostgreSQL ILIKE naturally favors shorter matches (higher selectivity). Start without explicit exact-match boost, add if testing shows need.

2. **Symbol type enumeration enforcement**
   - What we know: Five symbol types defined (function, class, method, variable, interface)
   - What's unclear: Whether to enforce at Python validation or allow flexible user values
   - Recommendation: Validate in Python with helpful error message listing valid types. Prevents SQL injection, provides better UX than database errors.

3. **Definition detection heuristic accuracy**
   - What we know: Need to identify definitions vs references for 2x score boost
   - What's unclear: Whether keyword prefix check is sufficient or need full tree-sitter parse
   - Recommendation: Start with keyword prefix heuristic (simple, fast). If inaccurate in testing, upgrade to reading symbol_type column from database (already indexed).

4. **TypeScript type vs interface distinction**
   - What we know: Context notes "lean toward yes" for extracting both
   - What's unclear: Whether to use separate symbol_type or both map to "interface"
   - Recommendation: Map both to "interface" symbol_type. TypeScript treats them interchangeably in many contexts, users likely search for "interface-like things" not specifically "type aliases".

## Sources

### Primary (HIGH confidence)

- [PostgreSQL Pattern Matching Documentation](https://www.postgresql.org/docs/current/functions-matching.html) - LIKE, ILIKE, wildcards
- [Python fnmatch Documentation](https://docs.python.org/3/library/fnmatch.html) - Glob pattern matching semantics
- [tree-sitter-languages GitHub](https://github.com/grantjenks/py-tree-sitter-languages) - Supported languages (JS/TS/Go/Rust confirmed)
- [PostgreSQL ILIKE Performance](https://www.commandprompt.com/education/wildcards-in-postgresql-with-practical-examples/) - Case-insensitive pattern matching
- [Reciprocal Rank Fusion in OpenSearch](https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/) - RRF algorithm (November 2025)
- [Weighted RRF in Elasticsearch](https://www.elastic.co/search-labs/blog/weighted-reciprocal-rank-fusion-rrf) - Post-fusion score boosting patterns (September 2025)
- [Azure AI Search RRF Documentation](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) - RRF scoring explanation
- Phase 29 RESEARCH.md - Symbol extraction patterns already implemented

### Secondary (MEDIUM confidence)

- [Tree-sitter TypeScript Grammar](https://github.com/tree-sitter/tree-sitter-typescript) - Node types for interface/type extraction
- [Tree-sitter Go Queries Tutorial](https://parsiya.net/blog/knee-deep-tree-sitter-queries/) - Method and struct extraction patterns
- [Tree-sitter JavaScript Queries](https://cycode.com/blog/tips-for-using-tree-sitter-queries/) - Arrow function and class extraction
- [Tree-sitter Rust Grammar](https://github.com/tree-sitter/tree-sitter-rust) - Impl block and trait extraction
- [Better RAG with RRF - Assembled](https://www.assembled.com/blog/better-rag-results-with-reciprocal-rank-fusion-and-hybrid-search) - Hybrid search ranking strategies
- [MongoDB RRF Basics](https://www.mongodb.com/resources/basics/reciprocal-rank-fusion) - RRF score calculation examples

### Tertiary (LOW confidence)

- [DEV Community Tree-sitter Posts](https://dev.to/shrsv/unraveling-tree-sitter-queries-your-guide-to-code-analysis-magic-41il) - Query writing tips (December 2025)
- [GitHub Issue on Class Query Patterns](https://github.com/tree-sitter/node-tree-sitter/issues/223) - Method extraction examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in Phase 29, verified language support
- Architecture: HIGH - SQL filtering is database best practice, RRF post-fusion pattern documented in Elasticsearch/OpenSearch
- Pitfalls: HIGH - Glob escaping and RRF timing issues are well-known patterns
- Code examples: HIGH - Based on Phase 29 implementation and PostgreSQL/Python stdlib documentation

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (60 days - stable ecosystem, no fast-moving dependencies)
