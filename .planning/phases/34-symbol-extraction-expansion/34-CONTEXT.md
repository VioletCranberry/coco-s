# Phase 34: Symbol Extraction Expansion - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend symbol extraction from 5 to 10 languages using external query files. Migrate from tree-sitter-languages to tree-sitter-language-pack. Add Java, C, C++, Ruby, and PHP symbol support.

</domain>

<decisions>
## Implementation Decisions

### Query file format
- One .scm file per language (queries/python.scm, queries/java.scm, etc.)
- User-extensible: check ~/.cocosearch/queries/ and project .cocosearch/queries/ for overrides
- Override priority: Project > User > Built-in
- Support inline documentation comments (;; @name, ;; @doc) in .scm files

### Symbol type coverage
- Language-appropriate: core symbols for all + language-specific extras
- Distinguish definition vs declaration (function_declaration vs function_definition for C/C++)
- Nested symbols always show parent context (ClassName.method_name) — extends Phase 33 behavior
- Extract symbol visibility (public/private/protected) as metadata where applicable (Java, PHP, C++)

### Error handling
- Skip file and warn once on parse failure — don't spam logs
- Files with missing query files get indexed without symbols (search still works)
- Track parse_failures count in `cocosearch stats` output
- Quiet by default: show count summary at end, -v for individual file warnings

### Migration approach
- Full replacement: remove tree-sitter-languages, use tree-sitter-language-pack for all
- Pin to specific tree-sitter-language-pack version
- Add individual bindings (tree-sitter-java etc.) for languages not in language-pack
- Migration requires re-indexing — users must re-index after upgrade

### Claude's Discretion
- Exact .scm query syntax and capture names
- Internal parser loading strategy
- Temp file handling during migration
- Specific version number for tree-sitter-language-pack

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

*Phase: 34-symbol-extraction-expansion*
*Context gathered: 2026-02-03*
