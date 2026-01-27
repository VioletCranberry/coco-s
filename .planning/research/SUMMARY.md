# Project Research Summary

**Project:** CocoSearch v1.2 -- DevOps Language Support
**Domain:** Semantic code search with DevOps-specific chunking and metadata (HCL/Terraform, Dockerfile, Bash/Shell)
**Researched:** 2026-01-27
**Confidence:** HIGH

## Executive Summary

CocoSearch v1.2 adds DevOps language support (HCL/Terraform, Dockerfile, Bash/Shell) through CocoIndex's existing `custom_languages` API with zero new runtime dependencies. The approach uses `CustomLanguageSpec` regex separators for chunking and Python stdlib `re` for metadata extraction. All three target languages lack Tree-sitter support in CocoIndex's built-in language list, making `custom_languages` the only viable chunking path. The architecture extends the existing single-flow pipeline rather than creating a parallel DevOps-specific index, keeping UX simple: users search one index for Python, Terraform, and Dockerfiles together.

The recommended approach is a four-phase build: (1) custom language definitions with file patterns and language routing, (2) metadata extraction as a CocoIndex op function, (3) flow integration with schema extension, and (4) search and output integration. This order follows hard dependencies -- chunking must produce correct boundaries before metadata extraction works, and metadata must be in the database before search can surface it. The key differentiator over grep/ripgrep is structural metadata: search results annotated with `resource.aws_s3_bucket.main` or `stage:builder` rather than raw text matches.

The primary risks are regex-based chunking splitting mid-block in HCL files with heredocs or deep nesting, metadata false positives from comments and string literals, and schema migration destroying existing indexes. All three are addressable: conservative top-level-only separators with generous chunk sizes (2000+ bytes) for chunking, line-start-anchored patterns for metadata, and additive-only schema changes with stable primary keys for migration. The regex approach is explicitly chosen as "good enough" for v1.2 -- a future upgrade path to `python-hcl2` (MIT) and `dockerfile-parse` (BSD) exists if deeper parsing proves necessary.

## Key Findings

### Recommended Stack

No new dependencies required. v1.2 is built entirely on CocoIndex's `custom_languages` parameter (already in `SplitRecursively`) and Python stdlib `re`. This is the strongest possible position for a milestone: zero dependency risk, zero supply chain additions, zero license concerns.

**Core technologies (unchanged from v1.1):**
- **CocoIndex >=0.3.28:** `SplitRecursively` with `custom_languages` param -- verified locally via `help()` and official docs
- **PostgreSQL + pgvector:** Three new TEXT columns added automatically by CocoIndex schema inference
- **Python stdlib `re`:** All metadata extraction via regex -- no external parsers needed
- **Rust `fancy-regex` engine:** CocoIndex's separator regex engine; supports lookaheads critical for split-before-boundary patterns

**Explicitly rejected dependencies:**
- `bashlex` -- GPLv3, incompatible with project MIT license
- `tfparse` -- requires `terraform init`, binary wheels, heavy
- `pyhcl` -- HCL v1 only, deprecated
- External Tree-sitter grammars -- bypasses CocoIndex pipeline

**Upgrade path if regex proves insufficient:** `python-hcl2` (MIT, v7.3.1) for HCL, `dockerfile-parse` (BSD, v2.0.1) for Dockerfile. Both license-compatible.

See: [STACK.md](STACK.md)

### Expected Features

**Must have (table stakes):**
- HCL block-level chunking (resource, module, variable boundaries)
- Dockerfile instruction-level chunking with FROM as stage boundary
- Bash function-level chunking
- File pattern recognition (`*.tf`, `Dockerfile`, `*.sh` and variants)
- Correct language routing (extension/filename to custom language spec)
- Block type metadata extraction (resource, FROM, function)
- Language filter additions (terraform, dockerfile, bash)
- Search results and MCP responses include metadata fields

**Should have (differentiators):**
- HCL resource hierarchy (`resource.aws_s3_bucket.data`) -- transforms results from "here is some HCL" to "here is the S3 bucket resource named data"
- Bash function name extraction (`function:deploy_app`)
- Graceful degradation for pre-v1.2 indexes (COALESCE fallback in SQL)
- Syntax highlighting for DevOps files in pretty output

**Defer to v1.3+:**
- Dockerfile stage tracking for non-FROM instructions (requires two-pass processing)
- Block type and hierarchy search filters (`--block-type`, `--hierarchy`)
- Terraform provider inference (aws_, azurerm_, google_ prefix heuristic)
- Bash script purpose annotation (path-based heuristics)

**Anti-features (deliberately NOT building):**
- Terraform plan/state integration, module resolution, secrets detection
- Dockerfile build graph analysis, linting integration
- Bash execution analysis, shell dialect detection
- Custom Tree-sitter grammar shipping

See: [FEATURES.md](FEATURES.md)

### Architecture Approach

Single-flow architecture with four integration points: (1) `SplitRecursively` constructor gains `custom_languages`, (2) new `extract_devops_metadata` CocoIndex op function runs after chunking, (3) PostgreSQL collector stores three new TEXT columns, and (4) search query and formatters surface metadata. Two new files (`languages.py`, `metadata.py`), five modified files (`config.py`, `flow.py`, `query.py`, `formatter.py`, `server.py`). Metadata extraction runs for ALL files (returning empty strings for non-DevOps), avoiding conditional flow branching.

**Major components:**
1. **Language definitions** (`languages.py`) -- `CustomLanguageSpec` constants for HCL, Dockerfile, Bash with hierarchical regex separators
2. **Metadata extractors** (`metadata.py`) -- `@cocoindex.op.function()` returning a `DevOpsMetadata` dataclass (block_type, hierarchy, language_id)
3. **Flow integration** (`flow.py`) -- passes `custom_languages` to constructor, adds metadata extraction step, extends collector fields
4. **Search integration** (`query.py`, `formatter.py`, `server.py`) -- new SearchResult fields, SQL SELECT extensions, metadata display in output

**Key patterns to follow:**
- Static language definitions (module-level constants, not dynamic)
- Metadata as CocoIndex op function (enables caching, incremental processing)
- Empty strings over NULLs for optional metadata (simpler SQL, consistent pattern)
- Graceful degradation via try/except on enriched query

See: [ARCHITECTURE.md](ARCHITECTURE.md)

### Critical Pitfalls

1. **Regex splits mid-block in HCL** -- Nested HCL blocks and heredocs confuse regex separators. Prevention: top-level-only separators, chunk_size 2000+ bytes, brace-balance validation, integration tests with real Terraform files containing heredocs and dynamic blocks.

2. **HCL heredocs trigger false splits** -- The word "resource" inside a JSON IAM policy heredoc triggers a false separator match. Prevention: line-start-anchored patterns (`r"\n(?:resource|data|...)\s+"`), generous chunk sizes so heredoc-containing blocks stay intact.

3. **Metadata false positives from comments/strings** -- Comments like `# This resource was replaced by aws_lambda_function` match extraction regex. Prevention: require structural context (line-start match, not mid-line), strip comments before extraction, write adversarial test cases.

4. **Schema migration destroys existing indexes** -- Adding collector fields changes CocoIndex's inferred schema. If primary keys change, tables are dropped and recreated. Prevention: keep primary keys as `["filename", "location"]` (unchanged), metadata as additive-only columns, test migration path explicitly before release.

5. **Dockerfile extensionless file detection** -- `Dockerfile` has no extension; current `extract_extension` returns empty string, causing plain-text fallback. Prevention: filename-to-language mapping function that checks basename before extension, prefix matching for `Dockerfile.dev` variants.

See: [PITFALLS.md](PITFALLS.md)

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Custom Language Definitions and File Routing

**Rationale:** Everything depends on correct chunking. If chunk boundaries are wrong, metadata extraction produces garbage, embeddings are poor, and search results are useless. Language detection and file patterns must work before any downstream feature.

**Delivers:** Three `CustomLanguageSpec` definitions (HCL, Dockerfile, Bash), file patterns in `IndexingConfig`, filename-to-language routing for extensionless files (Dockerfile), validation that custom separators are actually used.

**Features addressed:** HCL block-level chunking, Dockerfile instruction-level chunking, Bash function-level chunking, file pattern recognition, correct language routing.

**Pitfalls to avoid:** Regex splits mid-block (use top-level-only separators, 2000+ byte chunk_size), heredoc false splits (line-start-anchored patterns), Bash heredoc/quoting edge cases (conservative separators), language detection failure for Dockerfile (filename-based routing), custom vs. built-in Bash name collision (test early, rename if needed).

**Must validate:** Whether CocoIndex custom language names conflict with built-in Tree-sitter names for Bash. Whether chunk_size 2000+ produces acceptable results for typical Terraform repos. Whether `fancy-regex` lookahead patterns work as expected in separator context.

### Phase 2: Metadata Extraction

**Rationale:** Depends on Phase 1 producing well-bounded chunks. Metadata extraction regex matches the START of chunks -- if chunks start at block boundaries (as Phase 1 designs), regex works. If chunks start mid-block, extraction fails silently.

**Delivers:** `extract_devops_metadata` CocoIndex op function, HCL block type and hierarchy extraction, Dockerfile instruction type and FROM stage extraction, Bash function name extraction, `DevOpsMetadata` dataclass.

**Features addressed:** HCL block type identification, HCL resource hierarchy, Dockerfile instruction type, Bash function name, block type metadata.

**Pitfalls to avoid:** False positives from comments/strings (line-start anchoring, adversarial tests), performance overhead (pre-compile regex at module load, single-pass extraction), Dockerfile stage context limitation (simple approach: FROM chunks only for v1.2).

### Phase 3: Flow Integration and Schema

**Rationale:** Depends on both Phase 1 (language definitions) and Phase 2 (metadata extraction). This phase wires them into the existing CocoIndex pipeline and verifies the schema migration path.

**Delivers:** Modified `create_code_index_flow()` with `custom_languages` and metadata step, three new TEXT columns in chunks table, end-to-end indexing of DevOps files.

**Features addressed:** Flow integration, schema extension, non-DevOps files unaffected.

**Pitfalls to avoid:** Schema migration destroying existing indexes (stable primary keys, test migration before release), metadata running for all files (return empty strings for non-DevOps, no conditional branching).

### Phase 4: Search and Output Integration

**Rationale:** Depends on Phase 3 populating metadata in the database. This phase makes metadata visible to users and calling LLMs.

**Delivers:** Extended `SearchResult` with metadata fields, SQL queries selecting new columns, graceful degradation for pre-v1.2 indexes (try/except fallback), updated formatters (JSON and pretty), updated MCP server responses, new language filter values (terraform, dockerfile, bash).

**Features addressed:** Language filter for DevOps files, search results include metadata, MCP server metadata, graceful degradation, syntax highlighting for DevOps output.

**Pitfalls to avoid:** pgvector post-filter returning too few results with metadata filters (increase ef_search, over-fetch strategy), Dockerfile basename-based language filter (SQL LIKE pattern on filename).

### Phase Ordering Rationale

- **Strict dependency chain:** Language definitions -> Metadata extraction -> Flow integration -> Search integration. Each phase produces artifacts consumed by the next.
- **Phase 2 is unit-testable in parallel with Phase 1 validation:** Metadata extraction functions can be tested with synthetic chunk text while Phase 1 validates real chunking behavior.
- **Schema migration (Phase 3) is the highest-risk integration point:** Testing migration preserves data before building search features on top avoids wasted work if re-indexing is forced.
- **Phase 4 is lowest risk:** All search changes are additive and backward-compatible. COALESCE handles missing columns. Formatters show metadata only when present.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Needs `/gsd:research-phase` -- Bash custom vs. built-in name collision behavior, optimal chunk_size for DevOps files, `fancy-regex` separator pattern validation with real files. The FEATURES.md notes Bash IS in CocoIndex's built-in list, but STACK.md says it is NOT. This contradiction must be resolved by testing.
- **Phase 3:** Needs `/gsd:research-phase` -- CocoIndex schema migration behavior when adding columns, CocoIndex op function dataclass-to-column mapping verification, `collector.collect()` with struct fields.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Well-documented regex patterns for HCL/Dockerfile/Bash. Extraction logic is pure Python, fully unit-testable. No CocoIndex API uncertainties.
- **Phase 4:** Standard SQL SELECT extension, dataclass field additions, formatter updates. All patterns exist in the current codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies. CocoIndex API verified locally. All alternatives evaluated with license checks. |
| Features | HIGH | Table stakes clearly identified. Feature dependency graph mapped. MVP vs. defer boundary is well-defined. |
| Architecture | HIGH | Integration points verified against source code. CocoIndex op function patterns confirmed via official docs and examples. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls well-identified with prevention strategies. Regex edge cases (heredocs, nested blocks) need real-file validation. pgvector post-filter behavior needs benchmarking. |

**Overall confidence:** HIGH

### Gaps to Address

- **Bash built-in status contradiction:** FEATURES.md states Bash IS in CocoIndex's built-in Tree-sitter list; STACK.md states it is NOT. Both cite the same documentation. This must be resolved by runtime testing in Phase 1. If Bash is built-in, custom regex may be unnecessary or may conflict. If not built-in, custom regex is required.
- **CocoIndex schema migration behavior:** The exact behavior when adding non-primary-key columns to an existing table has not been tested. PITFALLS.md documents the risk; Phase 3 must validate before committing to the approach.
- **Chunk size optimization:** The recommended 2000+ bytes for DevOps files is based on structural analysis of typical Terraform resources. Real-world benchmarking is needed to find the right balance between semantic coherence and search granularity.
- **Dockerfile language routing:** How CocoIndex passes the `language` parameter for extensionless files (Dockerfile) is not fully documented. The `extract_extension` function returns empty string, which would fall through to plain text. A filename-based detection function is required, but how it integrates with the CocoIndex flow needs implementation-time validation.
- **pgvector post-filter adequacy:** When metadata filters are added in future (v1.3), filtered queries may return fewer results than requested. The mitigation strategies (increased ef_search, over-fetch) need benchmarking with realistic data volumes.

## Sources

### Primary (HIGH confidence)
- [CocoIndex Functions Documentation](https://cocoindex.io/docs/ops/functions) -- SplitRecursively API, CustomLanguageSpec, supported languages list, regex syntax
- [CocoIndex Custom Functions](https://cocoindex.io/docs/custom_ops/custom_functions) -- `@cocoindex.op.function()` decorator, return types
- [CocoIndex Academic Papers Example](https://cocoindex.io/docs/examples/academic_papers_index) -- CustomLanguageSpec usage pattern
- [CocoIndex Schema Inference Blog](https://cocoindex.io/blogs/handle-system-update-for-indexing-flow/) -- ALTER TABLE behavior
- [Terraform HCL Syntax Reference](https://developer.hashicorp.com/terraform/language/syntax/configuration) -- Block types, label patterns
- [Dockerfile Reference](https://docs.docker.com/reference/dockerfile/) -- All 19 instruction types
- [Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html) -- Function definition syntax
- CocoIndex Python API -- `help(SplitRecursively)`, `help(CustomLanguageSpec)` verified in local virtualenv
- CocoSearch source code -- `flow.py`, `query.py`, `formatter.py`, `server.py`, `config.py` integration points

### Secondary (MEDIUM confidence)
- [fancy-regex crate docs](https://docs.rs/fancy-regex/) -- Regex engine capabilities for separator patterns
- [pgvector 0.8.0 iterative scans](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/) -- Post-filter mitigation
- [python-hcl2](https://pypi.org/project/python-hcl2/) / [dockerfile-parse](https://pypi.org/project/dockerfile-parse/) -- Future upgrade path libraries
- [Tenable terrascan HCL parsing issues](https://github.com/tenable/terrascan/issues/233) -- Real-world nested block parsing failures

### Tertiary (LOW confidence)
- Competitive landscape analysis (Sourcegraph, GitHub Code Search) -- feature positioning, not technical validation
- Chunking strategy guides (Pinecone, Qdrant) -- general principles, not CocoIndex-specific

---
*Research completed: 2026-01-27*
*Ready for roadmap: yes*
