# Phase 21: Language Chunking Refactor - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor language chunking to use a registry pattern for clean extensibility. Separate module files for HCL, Dockerfile, and Bash. New languages added by creating a single module file. Existing chunking behavior unchanged.

</domain>

<decisions>
## Implementation Decisions

### Handler Interface
- Full chunker function: each handler exports a complete `chunk()` function
- Signature: `chunk(content: str, config: ChunkConfig) → list[Chunk]`
- Extensions declared as class attribute: `EXTENSIONS = ['.tf', '.hcl']`
- Protocol class pattern: each handler is a class implementing `LanguageHandler` protocol

### Discovery Mechanism
- Package scan: scan handlers/ directory, import all modules, find protocol implementers
- Eager at import: discovery happens when registry module is imported (catches errors early)
- Error on conflict: raise error if two handlers claim same extension
- Default text handler: use generic text chunker for unrecognized extensions

### Module Organization
- Location: `cocosearch/handlers/` — new top-level handlers package
- File naming: language name only — `hcl.py`, `dockerfile.py`, `bash.py`
- Registry and protocol in `handlers/__init__.py`
- Default handler as `text.py` in same directory

### Extension Workflow
- Copy template + implement: `handlers/_template.py` with TODOs
- Required test file: registry validates `test_<handler>.py` exists
- Documentation: `handlers/README.md` close to the code

### Claude's Discretion
- ChunkConfig structure and fields
- Exact protocol method signatures beyond chunk()
- Test file validation mechanism (startup vs CI)
- Text handler chunking strategy (paragraphs, lines, size-based)

</decisions>

<specifics>
## Specific Ideas

- Protocol pattern like Python's typing.Protocol for clean interface definition
- Underscore prefix (`_template.py`) to exclude from autodiscovery
- Fail-fast on extension conflicts to catch configuration errors early

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-language-chunking-refactor*
*Context gathered: 2026-02-01*
