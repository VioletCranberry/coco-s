---
phase: 29-symbol-aware-indexing
plan: 01
subsystem: indexer
tags: [tree-sitter, python, ast-parsing, symbol-extraction]

# Dependency graph
requires:
  - phase: 27-keyword-search
    provides: indexing flow with cocoindex transform functions
provides:
  - Tree-sitter-based Python symbol extraction module
  - extract_symbol_metadata() function for CocoIndex integration
  - Qualified method names (ClassName.method_name)
  - Graceful error handling for parse failures
affects: [29-02-symbol-indexing, 30-symbol-search]

# Tech tracking
tech-stack:
  added:
    - tree-sitter (0.21.3 - for AST parsing)
    - tree-sitter-languages (1.10.2 - pre-compiled Python grammar)
  patterns:
    - Tree-sitter query-based symbol extraction
    - Recursive AST walking with context tracking
    - NULL field returns for graceful degradation

key-files:
  created:
    - src/cocosearch/indexer/symbols.py
    - tests/unit/indexer/test_symbols.py
  modified:
    - pyproject.toml

key-decisions:
  - "Use tree-sitter 0.21.x for compatibility with tree-sitter-languages API"
  - "Detect async functions via AST child nodes, not text prefix"
  - "Skip nested functions (implementation details)"
  - "Return first symbol when chunk contains multiple"
  - "Qualified names for methods: ClassName.method_name"

patterns-established:
  - "Symbol extraction via recursive tree walking with class context"
  - "Async detection via node.children check for 'async' type"
  - "NULL fields (None) for non-Python, empty, or error cases"

# Metrics
duration: 6min
completed: 2026-02-03
---

# Phase 29 Plan 01: Symbol Extraction Module Summary

**Tree-sitter-based Python symbol extraction with qualified method names, async support, and graceful error handling**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-03T10:06:47Z
- **Completed:** 2026-02-03T10:12:59Z
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- Tree-sitter symbol extraction module with support for functions, classes, and methods
- Comprehensive unit test suite with 36 test cases covering all symbol types and edge cases
- Qualified method names (ClassName.method_name) for methods inside classes
- Async function detection and signature formatting
- Graceful error handling returning NULL fields for parse failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tree-sitter dependencies** - `8e5141d` (chore)
2. **Task 2: Create symbol extraction module** - `3d8c5ea` (feat)
3. **Task 3: Create unit tests for symbol extraction** - `337da38` (test)

## Files Created/Modified

- `pyproject.toml` - Added tree-sitter and tree-sitter-languages dependencies
- `src/cocosearch/indexer/symbols.py` - Symbol extraction module with extract_symbol_metadata() function
- `tests/unit/indexer/test_symbols.py` - 36 comprehensive unit tests

## Decisions Made

**Tree-sitter version compatibility:** Initially specified tree-sitter>=0.25.2, but discovered API incompatibility with tree-sitter-languages 1.10.2. The Language() constructor changed between 0.21 and 0.25. Downgraded to tree-sitter>=0.21.0,<0.22.0 for stable API compatibility. This is a known limitation documented in tree-sitter-languages.

**Async detection method:** Initially attempted to detect async functions by checking text before the function definition node. Discovered tree-sitter represents "async" as a child node of function_definition. Changed to `any(child.type == "async" for child in node.children)` for reliable detection.

**First symbol priority:** When a chunk contains multiple symbols (e.g., class with methods), return the first symbol found during tree walking. This means a chunk with "class Foo:\n    def bar():" returns the class symbol. Methods are extracted as separate symbols when they appear in their own chunks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed tree-sitter API version compatibility**
- **Found during:** Task 2 (Symbol extraction module creation)
- **Issue:** tree-sitter 0.25.2 changed Language() constructor API, causing TypeError with tree-sitter-languages 1.10.2
- **Fix:** Downgraded tree-sitter to 0.21.x range where API is stable
- **Files modified:** pyproject.toml
- **Verification:** `import tree_sitter_languages; get_language('python')` works without error
- **Committed in:** 3d8c5ea (Task 2 commit)

**2. [Rule 1 - Bug] Fixed async function signature detection**
- **Found during:** Task 2 (Symbol extraction module creation)
- **Issue:** Async detection via text prefix before function was unreliable
- **Fix:** Changed to check for "async" child node in function_definition AST node
- **Files modified:** src/cocosearch/indexer/symbols.py
- **Verification:** Test case for async functions passes with correct signature
- **Committed in:** 3d8c5ea (Task 2 commit)

**3. [Rule 1 - Bug] Fixed return type format missing arrow**
- **Found during:** Task 2 (Symbol extraction module creation)
- **Issue:** Return type extraction was missing the "->" arrow separator
- **Fix:** Added " -> " prefix when including return_type_node text in signature
- **Files modified:** src/cocosearch/indexer/symbols.py
- **Verification:** Test cases for return types show correct "-> Type" format
- **Committed in:** 3d8c5ea (Task 2 commit)

**4. [Rule 1 - Bug] Fixed class bases handling for classes without inheritance**
- **Found during:** Task 2 (Symbol extraction module creation)
- **Issue:** Classes without bases were getting "FooNone:" instead of "Foo:"
- **Fix:** Check if superclasses_node exists before extracting text
- **Files modified:** src/cocosearch/indexer/symbols.py
- **Verification:** Test case for simple class shows "class Foo:" not "class FooNone:"
- **Committed in:** 3d8c5ea (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (4 bugs)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep. Tree-sitter version constraint is stricter than planned but ensures stability.

## Issues Encountered

**Tree-sitter deprecation warning:** tree_sitter_languages.get_language() triggers a FutureWarning about deprecated Language constructor. This is a known issue in tree-sitter-languages 1.10.2 with tree-sitter 0.21.x. Warning is harmless (functionality works correctly) and will be resolved when tree-sitter-languages updates to support 0.25+ API. Suppressed in test output with grep filter to avoid noise.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 29-02 (Symbol Indexing):**
- extract_symbol_metadata() function ready for CocoIndex flow integration
- Returns dict with symbol_type, symbol_name, symbol_signature fields
- NULL handling (None values) for chunks without symbols
- Marked with @cocoindex.op.function() decorator for transform pipeline

**Known limitations:**
- Python-only support in Phase 29 (Plan 02 will integrate, Phase 30 adds more languages)
- Methods in chunks without class context are detected as functions
- Nested classes return outer class only (inner classes not extracted as separate symbols)

---
*Phase: 29-symbol-aware-indexing*
*Completed: 2026-02-03*
