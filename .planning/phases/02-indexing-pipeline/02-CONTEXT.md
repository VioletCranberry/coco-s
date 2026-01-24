# Phase 2: Indexing Pipeline - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a CocoIndex flow that indexes code files from a directory into PostgreSQL/pgvector. Users can index a codebase and have it stored as searchable embeddings with Tree-sitter-based semantic chunking. Includes .gitignore respect, include/exclude patterns, and incremental re-indexing.

</domain>

<decisions>
## Implementation Decisions

### Chunking granularity
- Chunk all semantic units: functions, classes, top-level statements, imports, constants
- Hierarchical nesting: methods include parent class name/signature as context for better embedding
- Rich metadata per chunk: file path, line range, symbol name, symbol type, parent chain, detected language, file last modified

### Language support
- Support all languages with Tree-sitter grammars (maximum flexibility)
- Fallback for files without parser: split by blank line groups (line-based chunks)
- Auto-exclude binary files and common generated patterns (node_modules, __pycache__, .git, vendor) in addition to .gitignore

### Index naming & storage
- Index name auto-derived from directory path (e.g., /home/user/myproject → 'myproject')
- Re-indexing same directory: incremental update (only process changed/new files, remove deleted)
- Store only references (file path + line range), not full chunk text — read file to show code
- Change detection: mtime first, hash only if mtime changed (balance speed and accuracy)

### CLI/API invocation
- Expose both CLI command and Python API (CLI wraps API)
- Progress reporting: progress bar during indexing + final summary
- Include/exclude patterns: config file (.cocosearch.yaml) for defaults, CLI flags can override
- Error handling: skip problematic files and continue, report all errors at end with file list

### Claude's Discretion
- Large chunk handling: determine approach for 500+ line functions based on embedding model constraints
- Language detection strategy: pick based on Tree-sitter capabilities (extension, shebang, etc.)

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

*Phase: 02-indexing-pipeline*
*Context gathered: 2026-01-24*
