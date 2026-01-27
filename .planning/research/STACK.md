# Technology Stack: v1.2 DevOps Language Support

**Project:** CocoSearch -- Local-first semantic code search via MCP
**Milestone:** v1.2 -- DevOps Language Support (HCL, Dockerfile, Bash)
**Researched:** 2026-01-27
**Confidence:** HIGH (CocoIndex API verified locally; parsing libraries verified via PyPI/official docs)

## Executive Summary

v1.2 requires **no new runtime dependencies** for its core functionality. CocoIndex's `SplitRecursively` with `custom_languages` handles chunking via regex patterns (using Rust's `fancy-regex` engine with lookahead support). Metadata extraction uses Python's stdlib `re` module -- no external parser libraries needed for the regex-based approach chosen in the architecture. Optional future enhancements could add `python-hcl2` or `dockerfile-parse` for deeper structural parsing, but these are not required for v1.2 goals.

## Recommended Stack

### Core (Unchanged from v1.0/v1.1)

| Technology | Version | Purpose | Status in v1.2 |
|------------|---------|---------|----------------|
| CocoIndex | >=0.3.28 | Indexing pipeline with `SplitRecursively` | **Unchanged** -- `custom_languages` param already exists |
| PostgreSQL + pgvector | pg17 / 0.8.1 | Vector storage | **Unchanged** -- new TEXT columns added automatically |
| Ollama (nomic-embed-text) | latest / 768-dim | Local embeddings | **Unchanged** |
| FastMCP (via `mcp[cli]`) | >=1.26.0 | MCP server interface | **Unchanged** |
| Python | >=3.11 | Runtime | **Unchanged** |
| UV | latest | Package manager | **Unchanged** |

### v1.2 Additions: Zero New Dependencies Required

| Component | Solution | Why No New Dependency |
|-----------|----------|----------------------|
| HCL chunking | `CustomLanguageSpec` with regex separators | CocoIndex built-in feature |
| Dockerfile chunking | `CustomLanguageSpec` with regex separators | CocoIndex built-in feature |
| Bash chunking | `CustomLanguageSpec` with regex separators | CocoIndex built-in feature |
| HCL metadata extraction | `re` module (stdlib) | Regex sufficient for block type/name extraction |
| Dockerfile metadata extraction | `re` module (stdlib) | Regex sufficient for instruction/stage extraction |
| Bash metadata extraction | `re` module (stdlib) | Regex sufficient for function name extraction |

### CocoIndex `custom_languages` API (Verified Locally)

The `SplitRecursively` constructor accepts `custom_languages: list[CustomLanguageSpec]` where each `CustomLanguageSpec` is a dataclass with:

```python
@dataclass
class CustomLanguageSpec:
    language_name: str           # e.g., "hcl"
    separators_regex: list[str]  # Hierarchical regex patterns (high-level first)
    aliases: list[str] = []      # e.g., ["tf", "tfvars"]
```

**Regex engine:** Rust `fancy-regex` crate -- supports lookaheads (`(?=...)`), lookbehinds (`(?<=...)`), backreferences, and atomic groups. This is critical because the chunking regex patterns use positive lookaheads to split before block boundaries without consuming the boundary text.

**Language matching logic** (verified from official docs):
1. Check `custom_languages` against `language_name` or `aliases` (case-insensitive)
2. Check built-in Tree-sitter languages (28 languages: Python, JS, Go, Rust, etc.)
3. Fallback to plain text

**Confirmed NOT in built-in language list:** HCL, Dockerfile. These require `custom_languages`.

**Confirmed in built-in language list:** Bash is NOT in CocoIndex's curated 28-language list despite Tree-sitter having a bash grammar. CocoIndex uses a fixed subset of tree-sitter-language-pack, and bash is absent from the documented supported languages table.

**Source:** Verified by running `help(cocoindex.functions.SplitRecursively)` and `help(cocoindex.functions.CustomLanguageSpec)` in the project virtualenv. Built-in language list confirmed from [CocoIndex Functions docs](https://cocoindex.io/docs/ops/functions).

## Alternatives Evaluated

### HCL/Terraform Parsing Libraries

| Library | Version | License | What It Does | Recommendation |
|---------|---------|---------|-------------|----------------|
| **python-hcl2** | 7.3.1 | MIT | Parse HCL2 into Python dicts using Lark | **NOT NEEDED for v1.2.** Useful for future deep parsing if regex metadata extraction proves insufficient. Safe to add later (MIT license, pure Python). |
| **python-hcl2-tf** | latest | MIT | Terraform-aware wrapper around python-hcl2 | **NOT NEEDED.** Overkill -- provides Terraform-specific dict structure, variable resolution. Only useful if we need to understand Terraform module semantics. |
| **tfparse** | 0.6.18 | Apache 2.0 | Full Terraform evaluation via Go bindings | **DO NOT USE.** Requires `terraform init` to resolve modules. Binary wheels only (macOS/Linux/Windows). Heavy dependency for metadata extraction. Designed for security scanning, not chunking. |
| **pyhcl** | 0.4.x | MPL 2.0 | HCL v1 parser | **DO NOT USE.** HCL v1 only. Modern Terraform uses HCL2. Legacy, not maintained for current Terraform syntax. |

**Rationale for regex-only approach:** HCL block boundaries follow a predictable pattern (`resource "type" "name" {`). The metadata we need (block kind, resource type, resource name) is extractable with a single regex. A full AST parser adds a dependency and complexity for no additional value in the v1.2 use case. If future milestones need to understand nested attributes, variable interpolation, or module dependencies, `python-hcl2` (MIT, pure Python) is the right upgrade path.

### Dockerfile Parsing Libraries

| Library | Version | License | What It Does | Recommendation |
|---------|---------|---------|-------------|----------------|
| **dockerfile-parse** | 2.0.1 | BSD-3-Clause | Parse Dockerfile into structured instructions | **NOT NEEDED for v1.2.** Provides `structure`, `labels`, `baseimage` properties. Useful for multi-stage build analysis. Could be a future enhancement. License-compatible (BSD). |
| **dockerfile** (asottile) | archived | MIT | Parse via Go's official parser | **DO NOT USE.** Archived/unmaintained since ~2023. |

**Rationale for regex-only approach:** Dockerfile instructions are line-oriented (`FROM`, `RUN`, `COPY`, etc.). A regex match on the first token of each line captures the instruction type perfectly. Multi-stage `FROM ... AS stage_name` is a simple regex. The `dockerfile-parse` library would provide multi-stage tracking and label extraction, but these are beyond v1.2 scope.

### Bash/Shell Parsing Libraries

| Library | Version | License | What It Does | Recommendation |
|---------|---------|---------|-------------|----------------|
| **bashlex** | 0.18 | **GPLv3** | Parse bash into AST (port of GNU bash parser) | **DO NOT USE.** GPLv3 license is incompatible with this project's MIT license. Adding bashlex as a dependency would require relicensing the project. |
| **tree-sitter-language-pack** | 0.13.0 | MIT/Apache | Pre-built tree-sitter grammars for 165+ languages | **NOT NEEDED for v1.2.** CocoIndex bundles its own tree-sitter integration. External tree-sitter access would bypass CocoIndex's pipeline. Useful only if building a standalone metadata extractor outside CocoIndex. |
| **tree-sitter-languages** | 1.10.x | Apache 2.0 | Legacy bundled tree-sitter grammars | **DO NOT USE.** Unmaintained. Successor is `tree-sitter-language-pack`. |

**Rationale for regex-only approach:** Bash function definitions follow two patterns: `func_name() {` and `function func_name`. These are trivially captured by regex. Control structures (`if`, `for`, `while`, `case`) are line-oriented. A full AST parser would help with nested constructs, but v1.2 only needs function names and top-level structure -- regex handles this cleanly.

**Critical licensing note:** bashlex is GPLv3. This project is MIT. GPLv3 dependencies are incompatible with MIT-licensed projects -- including bashlex would require either relicensing the project or removing it. This eliminates bashlex from consideration regardless of its technical merits.

## Tree-sitter Grammar Availability (Future Reference)

All three target languages have tree-sitter grammars, though CocoIndex does not include them in its built-in set:

| Language | Grammar Repository | License | In tree-sitter-language-pack | In CocoIndex Built-in |
|----------|-------------------|---------|-------|------|
| HCL | tree-sitter-grammars/tree-sitter-hcl | Apache 2.0 | Yes | **No** |
| Dockerfile | camdencheek/tree-sitter-dockerfile | MIT | Yes | **No** |
| Bash | tree-sitter/tree-sitter-bash | MIT | Yes | **No** |

**Why this matters for future:** If CocoIndex adds these languages to its built-in Tree-sitter support in a future version (the grammars exist, they just have not been included in CocoIndex's curated list), the custom regex separators would become unnecessary for chunking. The metadata extraction (`extract_devops_metadata`) would still be needed regardless, since Tree-sitter provides structural chunking but not semantic metadata like "this is an aws_s3_bucket resource."

## Installation (v1.2)

No changes to `pyproject.toml` dependencies. The v1.2 feature is implemented entirely with:
- CocoIndex's existing `custom_languages` parameter
- Python stdlib `re` module
- Python stdlib `os` module

```bash
# No new packages to install. Existing setup works:
uv sync
```

## What NOT to Use (and Why)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **bashlex** | GPLv3 -- incompatible with MIT license | Regex via `re` stdlib for function/structure extraction |
| **tfparse** | Requires `terraform init`, binary wheels, heavy | Regex for block type/name extraction |
| **pyhcl** | HCL v1 only, does not parse modern Terraform | Regex or `python-hcl2` (if needed) |
| **dockerfile** (asottile) | Archived, unmaintained | Regex or `dockerfile-parse` (if needed) |
| **tree-sitter-languages** | Unmaintained | `tree-sitter-language-pack` if external TS needed |
| **External tree-sitter for chunking** | Bypasses CocoIndex pipeline, adds complexity | CocoIndex `custom_languages` regex separators |
| **Full HCL/Dockerfile AST parsers** | Over-engineered for v1.2 metadata needs | Regex -- revisit if deeper parsing required |

## Upgrade Path (Post-v1.2)

If regex-based metadata extraction proves insufficient for future requirements:

| Trigger | Library to Add | Version | License | Purpose |
|---------|---------------|---------|---------|---------|
| Need nested HCL attribute parsing | `python-hcl2` | >=7.3.1 | MIT | Full HCL2 -> dict parsing |
| Need multi-stage Dockerfile tracking | `dockerfile-parse` | >=2.0.1 | BSD-3-Clause | Structured Dockerfile analysis |
| Need external tree-sitter AST access | `tree-sitter-language-pack` | >=0.13.0 | MIT/Apache 2.0 | Pre-built grammars for standalone parsing |

All upgrade options are MIT/BSD/Apache compatible with the project license. No license risk.

## Regex Engine Compatibility Note

The `separators_regex` patterns in `CustomLanguageSpec` are executed by CocoIndex's Rust core using the `fancy-regex` crate. Key differences from Python `re`:

| Feature | Python `re` | CocoIndex `fancy-regex` |
|---------|-------------|------------------------|
| Lookahead `(?=...)` | Supported | Supported |
| Lookbehind `(?<=...)` | Supported (fixed-width only) | Supported (variable-width) |
| Backreferences `\1` | Supported | Supported |
| Atomic groups `(?>...)` | Not supported | Supported |
| Unicode `\p{...}` | Limited | Full Unicode property support |
| `re.MULTILINE` flag | Via `(?m)` | Via `(?m)` |

**Practical implication:** Regex patterns for `separators_regex` should be tested in a Rust regex context, not just Python. The patterns used in v1.2 (lookaheads for block boundaries) work in both engines, so this is informational, not blocking.

## Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| CocoIndex `custom_languages` API | **HIGH** | Verified locally via `help()`, confirmed with official docs and examples |
| CocoIndex regex engine (fancy-regex) | **HIGH** | Official docs link to fancy-regex; lookahead patterns confirmed supported |
| No new dependencies needed | **HIGH** | Architecture uses only stdlib `re` + CocoIndex's existing API |
| Regex metadata extraction sufficiency | **MEDIUM** | Will handle common patterns; edge cases (heredocs, complex interpolation) may need refinement |
| Bash not in CocoIndex built-ins | **HIGH** | Verified against documented language list; bash/sh absent from the 28-language table |
| bashlex GPL incompatibility | **HIGH** | bashlex PyPI confirms GPLv3; project LICENSE confirms MIT |
| python-hcl2 as future upgrade | **HIGH** | PyPI confirms MIT, v7.3.1, Python >=3.7 |
| dockerfile-parse as future upgrade | **HIGH** | PyPI confirms BSD-3-Clause, v2.0.1 |

## Sources

**Verified via local environment:**
- `help(cocoindex.functions.SplitRecursively)` -- constructor signature, `custom_languages` parameter
- `help(cocoindex.functions.CustomLanguageSpec)` -- `language_name`, `separators_regex`, `aliases` fields
- `/Users/fzhdanov/GIT/personal/coco-s/LICENSE` -- MIT license confirmed

**Official documentation (HIGH confidence):**
- [CocoIndex Functions](https://cocoindex.io/docs/ops/functions) -- `SplitRecursively` API, `CustomLanguageSpec`, supported languages list, regex syntax reference
- [CocoIndex Academic Papers Example](https://cocoindex.io/examples/academic_papers_index) -- `CustomLanguageSpec` usage with `SplitRecursively` constructor
- [CocoIndex PDF Elements Example](https://cocoindex.io/examples/pdf_elements) -- another `CustomLanguageSpec` usage example
- [fancy-regex crate docs](https://docs.rs/fancy-regex/) -- regex syntax supported by CocoIndex separators
- [python-hcl2 PyPI](https://pypi.org/project/python-hcl2/) -- v7.3.1, MIT license, Python >=3.7
- [dockerfile-parse PyPI](https://pypi.org/project/dockerfile-parse/) -- v2.0.1, BSD-3-Clause license
- [bashlex PyPI](https://pypi.org/project/bashlex/) -- v0.18, GPLv3+ license
- [tree-sitter-language-pack PyPI](https://pypi.org/project/tree-sitter-language-pack/) -- v0.13.0, 165+ languages

**GitHub repositories (HIGH confidence):**
- [tree-sitter-grammars/tree-sitter-hcl](https://github.com/tree-sitter-grammars/tree-sitter-hcl) -- HCL grammar, Apache 2.0
- [tree-sitter/tree-sitter-bash](https://github.com/tree-sitter/tree-sitter-bash) -- Bash grammar, MIT
- [camdencheek/tree-sitter-dockerfile](https://github.com/camdencheek/tree-sitter-dockerfile) -- Dockerfile grammar, MIT
- [containerbuildsystem/dockerfile-parse](https://github.com/containerbuildsystem/dockerfile-parse) -- Dockerfile parser, BSD
- [amplify-education/python-hcl2](https://github.com/amplify-education/python-hcl2) -- HCL2 parser, MIT
- [idank/bashlex](https://github.com/idank/bashlex) -- Bash parser, GPLv3

**WebSearch findings (MEDIUM confidence, verified with official sources):**
- HCL/Terraform parsing ecosystem survey
- Dockerfile parsing library landscape
- Bash AST parsing options and licensing implications

---
*Stack research for: CocoSearch v1.2 DevOps Language Support*
*Researched: 2026-01-27*
