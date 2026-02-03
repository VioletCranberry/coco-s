# Phase 29: Symbol-Aware Indexing - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Index function and class definitions as first-class entities with metadata. Database schema adds symbol_type, symbol_name, symbol_signature columns. Python functions and classes are extracted during indexing. Existing pre-v1.7 indexes continue to work (symbols fields NULL). Symbol filtering/search is Phase 30.

</domain>

<decisions>
## Implementation Decisions

### Symbol Granularity
- Index functions, classes, and class methods as symbols
- Each method is its own symbol (e.g., MyClass.do_thing is separately searchable)
- Skip nested functions (functions inside functions) — they're implementation details
- Decorators captured as metadata but don't change symbol_type (method stays 'method')

### Metadata to Capture
- Three fields: symbol_name, symbol_type, symbol_signature
- symbol_name uses qualified names for methods: 'MyClass.do_thing' not 'do_thing'
- Docstrings not extracted separately (already in chunk content)
- Chunks without symbols have NULL symbol fields (not marked as 'module' or separate table)

### Parse Failure Handling
- Files that fail to parse are still indexed as chunks with NULL symbol fields
- Parse errors shown only in verbose mode (silent by default)
- If one function has issues, continue extracting other symbols from that file
- No special re-indexing for failed files — normal reindex handles changed files

### Signature Format
- Full signature as written: 'def process(self, data: list[str], limit: int = 10) -> dict'
- Classes use definition line: 'class MyClass(BaseClass, Mixin):'
- Decorators excluded from signature string
- Async keyword included: 'async def fetch(url: str) -> Response'

### Claude's Discretion
- Tree-sitter query patterns and implementation details
- Exact algorithm for extracting signature from AST
- How to handle edge cases not covered above
- Performance optimizations for symbol extraction

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-symbol-aware-indexing*
*Context gathered: 2026-02-03*
