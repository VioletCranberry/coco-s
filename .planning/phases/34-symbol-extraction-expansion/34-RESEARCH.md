# Phase 34: Symbol Extraction Expansion - Research

**Researched:** 2026-02-03
**Domain:** Tree-sitter symbol extraction, external query files, multi-language support
**Confidence:** HIGH

## Summary

Phase 34 extends symbol extraction from 5 languages (Python, JavaScript, TypeScript, Go, Rust) to 10 languages by adding Java, C, C++, Ruby, and PHP. The phase also migrates from the deprecated `tree-sitter-languages` package to `tree-sitter-language-pack` and introduces external `.scm` query files for user-extensible symbol patterns.

**Critical finding:** tree-sitter-language-pack 0.13.0 requires tree-sitter 0.25.x, while the project currently pins tree-sitter to 0.21.x. This is a breaking change requiring API migration (Parser constructor changes, QueryCursor replaces Query.captures()) and mandatory re-indexing after upgrade.

The tree-sitter ecosystem has standardized on tags.scm files for symbol tagging with capture conventions (@definition.class, @definition.function, @name). Each official language repository provides tags.scm files that can serve as templates for our custom queries.

**Primary recommendation:** Upgrade tree-sitter from 0.21.x to 0.25.x, replace tree-sitter-languages with tree-sitter-language-pack 0.13.0, and create external `.scm` query files following the standard tags.scm capture conventions.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tree-sitter | >=0.25.0,<0.26.0 | Parser generator | Required for tree-sitter-language-pack compatibility; current API |
| tree-sitter-language-pack | >=0.13.0 | Pre-built language parsers | 165+ languages, MIT/Apache licensed, maintained fork of tree-sitter-languages |
| pathlib | stdlib | Query file resolution | Standard library for path operations |

### Removed Dependencies

| Library | Reason |
|---------|--------|
| tree-sitter-languages | Deprecated, unmaintained, stuck on tree-sitter 0.21.x |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tree-sitter-language-pack | Individual language packages (tree-sitter-java, tree-sitter-c, etc.) | More control but 10+ separate dependencies, complex version management |
| tree-sitter-language-pack | tree-sitter-languages 1.10.2 | Unmaintained, deprecation warnings, incompatible with tree-sitter 0.25.x |
| External .scm files | Hardcoded Python queries | Not user-extensible, harder to maintain |
| tree-sitter 0.25.x | tree-sitter 0.21.x | 0.21 incompatible with tree-sitter-language-pack |

**Installation:**
```bash
# Update pyproject.toml:
# Remove: tree-sitter-languages>=1.10.0,<1.11.0
# Remove: tree-sitter>=0.21.0,<0.22.0
# Add:    tree-sitter>=0.25.0,<0.26.0
# Add:    tree-sitter-language-pack>=0.13.0

pip install "tree-sitter>=0.25.0,<0.26.0" "tree-sitter-language-pack>=0.13.0"
pip uninstall tree-sitter-languages
```

## Architecture Patterns

### Recommended Project Structure

```
src/cocosearch/
├── indexer/
│   ├── symbols.py          # Refactored: query-file-based extraction
│   └── queries/            # Built-in query files
│       ├── python.scm
│       ├── javascript.scm
│       ├── typescript.scm
│       ├── go.scm
│       ├── rust.scm
│       ├── java.scm        # NEW
│       ├── c.scm           # NEW
│       ├── cpp.scm         # NEW
│       ├── ruby.scm        # NEW
│       └── php.scm         # NEW

# User override locations (per CONTEXT.md):
~/.cocosearch/queries/          # User-level overrides
$PROJECT/.cocosearch/queries/   # Project-level overrides (highest priority)
```

### Pattern 1: External Query File Resolution

**What:** Load .scm query files from three locations with priority: Project > User > Built-in
**When to use:** Always for symbol extraction queries

**Example:**
```python
# Source: CONTEXT.md decision - Override priority: Project > User > Built-in
import importlib.resources
from pathlib import Path

def resolve_query_file(language: str, project_path: Path | None = None) -> str | None:
    """Resolve query file path with override priority."""
    query_name = f"{language}.scm"

    # Priority 1: Project-level override
    if project_path:
        project_query = project_path / ".cocosearch" / "queries" / query_name
        if project_query.exists():
            return project_query.read_text()

    # Priority 2: User-level override
    user_path = Path.home() / ".cocosearch" / "queries" / query_name
    if user_path.exists():
        return user_path.read_text()

    # Priority 3: Built-in queries
    try:
        return importlib.resources.files("cocosearch.indexer.queries").joinpath(query_name).read_text()
    except FileNotFoundError:
        return None  # Language not supported, index without symbols
```

### Pattern 2: tree-sitter-language-pack API Usage

**What:** New API for getting parsers (different from tree-sitter-languages)
**When to use:** All parser initialization

**Example:**
```python
# OLD API (tree-sitter-languages 1.10.x + tree-sitter 0.21.x)
from tree_sitter import Parser
from tree_sitter_languages import get_language

parser = Parser()
parser.set_language(get_language("python"))

# NEW API (tree-sitter-language-pack 0.13.0 + tree-sitter 0.25.x)
from tree_sitter_language_pack import get_parser, get_language

# Option 1: Get pre-configured parser directly (RECOMMENDED)
parser = get_parser("python")

# Option 2: Get language and configure parser manually
from tree_sitter import Parser
language = get_language("python")
parser = Parser(language)  # Note: language passed to constructor, not set_language()
```

### Pattern 3: Query-Based Symbol Extraction (tree-sitter 0.25.x API)

**What:** Use Query + QueryCursor API for executing queries
**When to use:** All symbol extraction operations

**Example:**
```python
# Source: py-tree-sitter 0.25.x documentation
from tree_sitter import Query
from tree_sitter_language_pack import get_language, get_parser

def extract_symbols_with_query(source_code: str, language_name: str, query_text: str) -> list[dict]:
    """Extract symbols using external query file."""
    language = get_language(language_name)
    parser = get_parser(language_name)

    tree = parser.parse(bytes(source_code, "utf8"))

    # Create Query from .scm file content
    query = Query(language, query_text)

    # Execute query - captures() returns list of (node, capture_name) tuples
    captures = query.captures(tree.root_node)

    symbols = []
    # Group captures by definition type
    for node, capture_name in captures:
        if capture_name.startswith("definition."):
            symbol_type = capture_name.split(".", 1)[1]  # "class", "function", etc.
            # Find the @name capture for this definition
            name_node = node.child_by_field_name("name")
            if name_node:
                symbol_name = source_code[name_node.start_byte:name_node.end_byte]
                symbols.append({
                    "symbol_type": map_symbol_type(symbol_type),
                    "symbol_name": symbol_name,
                    "symbol_signature": build_signature(source_code, node),
                })

    return symbols

def map_symbol_type(raw_type: str) -> str:
    """Map query capture types to database symbol types."""
    # Normalize to existing schema: function, class, method, interface
    mapping = {
        "function": "function",
        "method": "method",
        "class": "class",
        "interface": "interface",
        "struct": "class",      # Map struct to class
        "enum": "class",        # Map enum to class
        "trait": "interface",   # Map trait to interface
        "module": "class",      # Map module to class (Ruby, PHP)
        "namespace": "class",   # Map namespace to class (C++, PHP)
        "type": "interface",    # Map type alias to interface
    }
    return mapping.get(raw_type, "function")
```

### Pattern 4: Standard tags.scm Query Format

**What:** Use tree-sitter's standard tags.scm capture conventions
**When to use:** All .scm query files for symbol extraction

**Example:**
```scheme
;; java.scm - Symbol extraction query for Java
;; Source: https://github.com/tree-sitter/tree-sitter-java/blob/master/queries/tags.scm

;; Class declarations
(class_declaration
  name: (identifier) @name) @definition.class

;; Interface declarations
(interface_declaration
  name: (identifier) @name) @definition.interface

;; Enum declarations
(enum_declaration
  name: (identifier) @name) @definition.enum

;; Method declarations
(method_declaration
  name: (identifier) @name) @definition.method

;; Constructor declarations
(constructor_declaration
  name: (identifier) @name) @definition.method
```

### Pattern 5: Qualified Names with Parent Context

**What:** Build qualified symbol names (ClassName.method_name) by traversing parent nodes
**When to use:** Methods, nested classes, module members - extends Phase 33 behavior

**Example:**
```python
# Source: CONTEXT.md - Nested symbols always show parent context
def build_qualified_name(node, source_code: str, language: str) -> str:
    """Build qualified name with parent context.

    Examples:
    - Java method: "MyClass.myMethod"
    - C++ method: "MyNamespace::MyClass::myMethod"
    - Ruby method: "MyModule::MyClass.instance_method"
    - PHP method: "MyNamespace\\MyClass::myMethod"
    """
    name = get_node_name(node, source_code)
    parents = []

    parent = node.parent
    while parent is not None:
        if is_container_node(parent, language):
            parent_name = get_node_name(parent, source_code)
            if parent_name:
                parents.append(parent_name)
        parent = parent.parent

    if not parents:
        return name

    # Language-specific separator
    separator = get_separator(language)
    return separator.join(reversed(parents)) + separator + name

def get_separator(language: str) -> str:
    """Get language-specific name separator."""
    separators = {
        "cpp": "::",
        "php": "\\",  # or :: for static methods
    }
    return separators.get(language, ".")

def is_container_node(node, language: str) -> bool:
    """Check if node is a container (class, module, namespace)."""
    container_types = {
        "java": ["class_declaration", "interface_declaration", "enum_declaration"],
        "c": ["struct_specifier"],
        "cpp": ["class_specifier", "struct_specifier", "namespace_definition"],
        "ruby": ["class", "module"],
        "php": ["class_declaration", "interface_declaration", "trait_declaration", "namespace_definition"],
    }
    return node.type in container_types.get(language, [])
```

### Pattern 6: Visibility Extraction (Java, PHP, C++)

**What:** Extract public/private/protected visibility from language-specific modifier nodes
**When to use:** Per CONTEXT.md: "Extract symbol visibility as metadata where applicable"

**Example:**
```python
# Source: CONTEXT.md decision
def extract_visibility(node, source_code: str, language: str) -> str | None:
    """Extract visibility modifier from declaration node."""
    if language == "java":
        # Java: modifiers child contains access level
        for child in node.children:
            if child.type == "modifiers":
                text = source_code[child.start_byte:child.end_byte]
                if "public" in text:
                    return "public"
                elif "private" in text:
                    return "private"
                elif "protected" in text:
                    return "protected"
        return None  # Package-private (default)

    elif language == "php":
        # PHP: visibility_modifier is sibling child
        for child in node.children:
            if child.type == "visibility_modifier":
                return source_code[child.start_byte:child.end_byte].lower()
        return "public"  # PHP default

    elif language == "cpp":
        # C++: Access specifier from class body context
        # Would need to track current access level while traversing
        return None  # Defer to future enhancement

    return None
```

### Anti-Patterns to Avoid

- **Hardcoding queries in Python:** Use external .scm files for user extensibility per CONTEXT.md
- **Using tree-sitter-languages 1.10.2:** Deprecated, causes warnings, incompatible with tree-sitter 0.25.x
- **Using Parser.set_language() in new code:** Use `get_parser()` or `Parser(language)` constructor
- **Ignoring parse failures:** Track parse_failures count per CONTEXT.md error handling decision
- **Spamming logs on failures:** Per CONTEXT.md: "Skip file and warn once, don't spam logs"

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-language parser loading | Custom grammar compilation | tree-sitter-language-pack.get_parser() | Pre-compiled wheels, zero build dependencies |
| Query pattern matching | Imperative AST traversal | tree-sitter Query + captures() | Declarative, maintainable, ecosystem standard |
| Query file parsing | Custom .scm parser | tree-sitter Query constructor | Validates syntax, reports errors |
| Symbol type normalization | Per-language if/else chains | Capture naming convention (@definition.*) | Unified extraction logic |
| C/C++ macro expansion | Preprocessor implementation | Skip problematic files, track failures | Tree-sitter parses source directly |

**Key insight:** The current symbols.py has 800+ lines of manual AST traversal for 5 languages. External .scm files will be ~30-50 lines per language and leverage tree-sitter's optimized query engine.

## Common Pitfalls

### Pitfall 1: tree-sitter Version Mismatch (CRITICAL)

**What goes wrong:** tree-sitter-language-pack fails to import or produces errors
**Why it happens:** tree-sitter-language-pack 0.13.0 requires tree-sitter 0.25.x; current project uses 0.21.x
**How to avoid:** Upgrade tree-sitter to 0.25.x BEFORE installing tree-sitter-language-pack
**Warning signs:** ImportError, AttributeError on Parser, "Language" constructor errors

### Pitfall 2: Parser API Change

**What goes wrong:** `parser.set_language(lang)` silently fails or behaves differently
**Why it happens:** tree-sitter 0.22+ changed Parser initialization; `Parser(language)` constructor preferred
**How to avoid:** Use `get_parser()` from language-pack which returns fully configured parser
**Warning signs:** Parser works but produces empty trees or wrong node types

### Pitfall 3: Query.captures() API Change

**What goes wrong:** Code expects list but gets different structure
**Why it happens:** py-tree-sitter 0.25.x captures() returns list of (node, capture_name) tuples
**How to avoid:** Use iteration pattern: `for node, capture_name in query.captures(root_node):`
**Warning signs:** TypeError when accessing captures, incorrect capture handling

### Pitfall 4: C/C++ Parse Failures on Macro-Heavy Code

**What goes wrong:** Files with heavy macro usage fail to parse or produce invalid AST
**Why it happens:** Tree-sitter parses source text directly, doesn't expand macros
**How to avoid:** Per CONTEXT.md: skip file, warn once, track parse_failures in stats
**Warning signs:** High failure rate on system headers, kernel code, heavily preprocessed files

### Pitfall 5: C Function Declaration vs Definition

**What goes wrong:** Forward declarations (no body) extracted as symbols, cluttering results
**Why it happens:** Both use similar node structure
**How to avoid:** Query for function_definition (has compound_statement body), not declarations
**Warning signs:** Duplicate symbols for same function (declaration in .h + definition in .c)

### Pitfall 6: Missing Parent Context for Methods

**What goes wrong:** Methods extracted as standalone functions without class context
**Why it happens:** Query captures method node but doesn't traverse to parent class
**How to avoid:** Walk parent chain to build qualified name per Phase 33 pattern
**Warning signs:** Multiple results named "initialize", "constructor", "__init__" without class prefix

### Pitfall 7: Cache/Reindex Required After Migration

**What goes wrong:** Old indexed data has stale symbol information
**Why it happens:** Migration changes extraction logic; existing index uses old extraction
**How to avoid:** Per CONTEXT.md: "Migration requires re-indexing - users must re-index after upgrade"
**Warning signs:** New language files don't have symbols; old files show old symbol patterns

## Code Examples

### Java Query File (queries/java.scm)

```scheme
;; Source: https://github.com/tree-sitter/tree-sitter-java/blob/master/queries/tags.scm
;; @doc Java symbol extraction: classes, interfaces, enums, methods

(class_declaration
  name: (identifier) @name) @definition.class

(interface_declaration
  name: (identifier) @name) @definition.interface

(enum_declaration
  name: (identifier) @name) @definition.enum

(method_declaration
  name: (identifier) @name) @definition.method

(constructor_declaration
  name: (identifier) @name) @definition.method
```

### C Query File (queries/c.scm)

```scheme
;; Source: https://github.com/tree-sitter/tree-sitter-c/blob/master/queries/tags.scm
;; @doc C symbol extraction: functions, structs, enums, typedefs

;; Functions (definitions only - have body)
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @definition.function

;; Structs (with body)
(struct_specifier
  name: (type_identifier) @name
  body: (_)) @definition.struct

;; Enums
(enum_specifier
  name: (type_identifier) @name) @definition.enum

;; Typedefs
(type_definition
  declarator: (type_identifier) @name) @definition.type
```

### C++ Query File (queries/cpp.scm)

```scheme
;; Source: https://github.com/tree-sitter/tree-sitter-cpp/blob/master/queries/tags.scm
;; @doc C++ symbol extraction: functions, classes, structs, namespaces

;; Classes
(class_specifier
  name: (type_identifier) @name) @definition.class

;; Structs
(struct_specifier
  name: (type_identifier) @name
  body: (_)) @definition.struct

;; Namespaces
(namespace_definition
  name: (namespace_identifier) @name) @definition.namespace

;; Functions
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @definition.function

;; Methods (qualified names)
(function_definition
  declarator: (function_declarator
    declarator: (qualified_identifier) @name)) @definition.method
```

### Ruby Query File (queries/ruby.scm)

```scheme
;; Source: https://github.com/tree-sitter/tree-sitter-ruby/blob/master/queries/tags.scm
;; @doc Ruby symbol extraction: methods, classes, modules

;; Methods (instance)
(method
  name: (_) @name) @definition.method

;; Singleton methods (class methods: def self.foo)
(singleton_method
  name: (_) @name) @definition.method

;; Classes
(class
  name: [(constant) (scope_resolution)] @name) @definition.class

;; Modules
(module
  name: [(constant) (scope_resolution)] @name) @definition.module
```

### PHP Query File (queries/php.scm)

```scheme
;; Source: https://github.com/tree-sitter/tree-sitter-php/blob/master/php/queries/tags.scm
;; @doc PHP symbol extraction: functions, classes, interfaces, traits, methods

;; Functions
(function_definition
  name: (name) @name) @definition.function

;; Classes
(class_declaration
  name: (name) @name) @definition.class

;; Interfaces
(interface_declaration
  name: (name) @name) @definition.interface

;; Traits
(trait_declaration
  name: (name) @name) @definition.trait

;; Methods
(method_declaration
  name: (name) @name) @definition.method
```

### Parser Migration (symbols.py refactor)

```python
# BEFORE (current code in symbols.py)
from tree_sitter import Parser
from tree_sitter_languages import get_language

_PARSERS: dict[str, Parser] = {}

def _get_parser(language: str) -> Parser:
    global _PARSERS
    if language not in _PARSERS:
        lang = get_language(language)
        parser = Parser()
        parser.set_language(lang)
        _PARSERS[language] = parser
    return _PARSERS[language]

# AFTER (migrated to tree-sitter-language-pack)
from tree_sitter_language_pack import get_parser as pack_get_parser

_PARSERS: dict[str, Parser] = {}

def _get_parser(language: str) -> Parser:
    global _PARSERS
    if language not in _PARSERS:
        _PARSERS[language] = pack_get_parser(language)
    return _PARSERS[language]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tree-sitter-languages 1.10.x | tree-sitter-language-pack 0.13.0 | Nov 2025 | tree-sitter-languages deprecated, language-pack is maintained fork |
| tree-sitter 0.21.x | tree-sitter 0.25.x | May 2024+ | API changes for Parser constructor, Language loading |
| Parser.set_language() | Parser(language) constructor | tree-sitter 0.22+ | Initialization pattern changed |
| Hardcoded Python AST traversal | External .scm query files | tree-sitter standard | Maintainable, user-extensible |
| Manual symbol extraction | Query captures | tree-sitter standard | Declarative patterns, efficient matching |

**Deprecated/outdated:**
- **tree-sitter-languages 1.10.x**: No longer maintained since mid-2024, stuck on tree-sitter 0.21
- **Parser.set_language()**: Works but 0.25 prefers `Parser(language)` constructor
- **Language(path, name)**: Removed in 0.22; use get_language() from language-pack instead

## Open Questions

1. **C/C++ parse failure rate on real codebases**
   - What we know: C/C++ code often uses macros, preprocessor directives that tree-sitter struggles with
   - What's unclear: Expected failure rate on production codebases (5%? 20%?)
   - Recommendation: Test on real C/C++ codebases during implementation; track parse_failures in stats
   - Note: SUMMARY.md flags this for validation: "Test C/C++ extraction on real codebases, verify failure rates"

2. **Query file documentation format**
   - What we know: CONTEXT.md specifies ";; @name, ;; @doc" comments in .scm files
   - What's unclear: Exact structured format expected
   - Recommendation: Use `;; @doc Description` as first comment in each file

3. **Ruby singleton vs instance method representation**
   - What we know: Ruby grammar distinguishes singleton_method and method node types
   - What's unclear: Whether to use Class.method vs Class#method convention
   - Recommendation: Use standard Ruby docs convention: Class.singleton_method, Class#instance_method

4. **Symbol visibility storage**
   - What we know: CONTEXT.md says extract visibility (public/private/protected) as metadata
   - What's unclear: Whether to add database column or use existing metadata field
   - Recommendation: Start by storing in existing metadata fields; add column if filtering needed

## Sources

### Primary (HIGH confidence)

- [tree-sitter-language-pack PyPI](https://pypi.org/project/tree-sitter-language-pack/) - Version 0.13.0, Nov 2025, requires tree-sitter 0.25.x
- [tree-sitter-language-pack GitHub](https://github.com/Goldziher/tree-sitter-language-pack) - API: get_binding(), get_language(), get_parser()
- [py-tree-sitter 0.25.2 docs](https://tree-sitter.github.io/py-tree-sitter/) - Current Python API documentation
- [Tree-sitter Query Syntax](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html) - Official query syntax: S-expressions, field names, captures
- [Tree-sitter Query Operators](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/2-operators.html) - Quantification (+, *, ?), alternations [], anchors

### Secondary (MEDIUM confidence)

- [tree-sitter-java node-types.json](https://github.com/tree-sitter/tree-sitter-java/blob/master/src/node-types.json) - Java: class_declaration, method_declaration, interface_declaration, enum_declaration, constructor_declaration
- [tree-sitter-c node-types.json](https://github.com/tree-sitter/tree-sitter-c/blob/master/src/node-types.json) - C: function_definition, struct_specifier, enum_specifier, type_definition
- [tree-sitter-cpp node-types.json](https://github.com/tree-sitter/tree-sitter-cpp/blob/master/src/node-types.json) - C++: function_definition, class_specifier, struct_specifier, namespace_definition
- [tree-sitter-ruby node-types.json](https://github.com/tree-sitter/tree-sitter-ruby/blob/master/src/node-types.json) - Ruby: method, class, module, singleton_method
- [py-tree-sitter Discussion #251](https://github.com/tree-sitter/py-tree-sitter/discussions/251) - API changes from 0.21 to 0.22+: Language loading

### Tertiary (LOW confidence)

- [Medium: Understanding Tree-sitter Query Syntax](https://medium.com/@linz07m/understanding-tree-sitter-query-syntax-def33e33a9d2) - Community tutorial
- [DeepWiki: tree-sitter-java Query System](https://deepwiki.com/tree-sitter/tree-sitter-java/4.2-query-system) - Additional examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - tree-sitter-language-pack officially maintained, version requirements documented on PyPI
- Architecture: HIGH - tags.scm is tree-sitter ecosystem standard, capture conventions well-documented
- API migration: HIGH - py-tree-sitter docs + GitHub discussions document 0.21->0.25 changes
- Pitfalls: MEDIUM - C/C++ failure rates need validation on real codebases (flagged in SUMMARY.md)
- Node types: MEDIUM - Derived from official node-types.json; may need refinement during testing

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (60 days - tree-sitter ecosystem stable, language-pack actively maintained)
