# Phase 2: Metadata Extraction - Research

**Researched:** 2026-01-27
**Domain:** Python regex-based text extraction from DevOps file chunks (HCL, Dockerfile, Bash)
**Confidence:** HIGH

## Summary

This phase creates a standalone `metadata.py` module that extracts structured metadata from DevOps file chunks using Python's `re` module. The module receives chunk text (produced by Phase 1's `SplitRecursively` with custom language separators) and returns a `DevOpsMetadata` dataclass with `block_type`, `hierarchy`, and `language_id` fields.

The research confirmed: (1) CocoIndex supports `@dataclass` return types from `@cocoindex.op.function()` decorated functions -- each dataclass field maps to a database column; (2) the Phase 1 separators include `\n` + keyword, meaning chunks will start with the block keyword (e.g., `resource`, `FROM`, `function`) after whitespace stripping; (3) HCL has 12 top-level block types with 0, 1, or 2 labels; Dockerfile has 18 instructions; Bash has 3 function definition syntaxes.

**Primary recommendation:** Build per-language extraction functions that match block keywords at the start of chunk text (after stripping leading whitespace and skipping comment lines), returning a `DevOpsMetadata` dataclass. Use `re.compile()` for all patterns to avoid recompilation overhead on every chunk.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `re` | stdlib (3.11+) | Regex pattern matching for block extraction | Zero dependencies, sufficient for line-start matching |
| Python `dataclasses` | stdlib (3.11+) | `DevOpsMetadata` return type | CocoIndex maps dataclass fields to DB columns |
| `cocoindex` | >=0.3.28 | `@cocoindex.op.function()` decorator | Required for flow integration (Phase 3) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | - | - | No supporting libraries needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `re` | `regex` package | Better Unicode/POSIX but adds dependency; `re` is sufficient for ASCII keyword matching |
| `dataclass` | `NamedTuple` | Immutable but less readable for 3-field struct; dataclass matches existing codebase pattern |
| `dataclass` | Pydantic `BaseModel` | Validation built-in but heavier; CocoIndex docs show dataclass as idiomatic |

**Installation:**
```bash
# No new packages needed -- all stdlib + existing cocoindex
```

## Architecture Patterns

### Recommended Project Structure
```
src/cocosearch/indexer/
    metadata.py          # NEW: DevOpsMetadata dataclass + extraction functions
    languages.py         # EXISTING: CustomLanguageSpec definitions (Phase 1)
    embedder.py          # EXISTING: extract_language, extract_extension
    flow.py              # EXISTING: modified in Phase 3 to call metadata extraction
```

### Pattern 1: Dataclass Return from @cocoindex.op.function()
**What:** Define a `@dataclass` and use it as the return type annotation on a CocoIndex op function. Each field becomes a column in the output table.
**When to use:** When a CocoIndex function needs to return multiple named values.
**Example:**
```python
# Source: CocoIndex docs - https://cocoindex.io/docs/core/data_types
# Source: Academic papers indexing example
import dataclasses
import cocoindex

@dataclasses.dataclass
class DevOpsMetadata:
    block_type: str    # e.g., "resource", "FROM", "function"
    hierarchy: str     # e.g., "resource.aws_s3_bucket.data", "stage:builder"
    language_id: str   # e.g., "hcl", "dockerfile", "bash"

@cocoindex.op.function()
def extract_devops_metadata(text: str, language: str) -> DevOpsMetadata:
    """Extract metadata from a chunk. language comes from extract_language."""
    ...
    return DevOpsMetadata(block_type="resource", hierarchy="resource.aws_s3_bucket.data", language_id="hcl")
```
**Confidence:** HIGH -- verified from CocoIndex official docs and multiple examples (academic papers, multi-format indexing).

### Pattern 2: Per-Language Extraction Functions (Internal, Not Decorated)
**What:** Separate plain Python functions for each language's extraction logic. The `@cocoindex.op.function()` decorated function dispatches to these.
**When to use:** Always -- keeps each language's regex logic isolated and independently testable.
**Example:**
```python
def extract_hcl_metadata(text: str) -> DevOpsMetadata:
    """Extract from HCL chunk. Pure Python, no CocoIndex dependency."""
    ...

def extract_dockerfile_metadata(text: str) -> DevOpsMetadata:
    """Extract from Dockerfile chunk. Pure Python, no CocoIndex dependency."""
    ...

def extract_bash_metadata(text: str) -> DevOpsMetadata:
    """Extract from Bash chunk. Pure Python, no CocoIndex dependency."""
    ...
```
**Confidence:** HIGH -- matches CONTEXT.md decision for "separate extraction functions per language."

### Pattern 3: Comment Line Stripping Before Matching
**What:** Strip leading comment lines from chunk text before applying block-keyword regex. Each language has different comment syntax.
**When to use:** Always -- prevents false positives from comments like `# This resource was replaced`.
**Example:**
```python
import re

# Per-language comment patterns
_HCL_COMMENT_LINE = re.compile(r'^(?:\s*#|\s*//|\s*/\*).*$', re.MULTILINE)
_DOCKERFILE_COMMENT_LINE = re.compile(r'^\s*#.*$', re.MULTILINE)
_BASH_COMMENT_LINE = re.compile(r'^\s*#.*$', re.MULTILINE)

def _strip_leading_comments(text: str, comment_pattern: re.Pattern) -> str:
    """Strip leading comment/blank lines from chunk text."""
    lines = text.lstrip().split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not comment_pattern.match(line):
            return '\n'.join(lines[i:])
    return ""
```
**Confidence:** HIGH -- matches CONTEXT.md decision for "explicitly skip comment lines before matching block keywords."

### Anti-Patterns to Avoid
- **Matching anywhere in chunk text:** Only match at the start (after comment stripping). Mid-chunk keywords are nested blocks or string content, not the chunk's identity.
- **Single monolithic regex:** Do NOT build one massive regex for all languages. Per-language functions are clearer and independently testable.
- **Case-insensitive matching for Dockerfile:** Dockerfile instructions are uppercase by convention. The Phase 1 separators already use uppercase. Match case-sensitively.
- **Forgetting empty-string defaults:** Every code path must return `DevOpsMetadata` with empty strings for any field that cannot be extracted. Never return None.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dataclass-to-column mapping | Custom serialization | `@dataclasses.dataclass` with `@cocoindex.op.function()` | CocoIndex natively maps dataclass fields to Struct columns |
| Language routing | If-else chain on file extensions | Reuse `extract_language()` from `embedder.py` | Already handles Dockerfile/Containerfile naming, extension mapping |
| HCL block type enumeration | Hardcoded strings scattered in code | Compile-time constant tuple/set | Single source of truth for the 12 known block keywords |

**Key insight:** The CocoIndex framework already handles the dataclass-to-column mapping. The metadata module should focus purely on regex extraction and return a dataclass instance. Serialization, column creation, and storage are Phase 3 concerns.

## Common Pitfalls

### Pitfall 1: False Positives from Comments (Critical -- from Roadmap Pitfall 3)
**What goes wrong:** A comment like `# This resource was replaced` at the start of a chunk triggers `block_type=resource` extraction.
**Why it happens:** Naive regex like `r'resource\s+'` matches inside comments.
**How to avoid:** Strip leading comment lines before applying block-keyword matching. HCL comments use `#`, `//`, and `/* */`. Dockerfile and Bash comments use `#`.
**Warning signs:** Test with chunks that start with comment lines containing block keywords.

### Pitfall 2: Bash Function Name Patterns (Two Syntaxes)
**What goes wrong:** Only matching `function name` misses the POSIX `name() {` syntax, which is the most common style.
**Why it happens:** The Phase 1 Bash separator only splits on `\nfunction ` -- POSIX-style functions without the `function` keyword get split by blank lines (Level 2) instead.
**How to avoid:** The metadata regex must match BOTH:
  - `function deploy_app() {` or `function deploy_app {` (starts with `function`)
  - `deploy_app() {` (starts with function name directly, no `function` keyword)
The success criteria explicitly show `deploy_app() {` as a test case.
**Warning signs:** Test with both function definition syntaxes.

### Pitfall 3: HCL Block Label Count Varies (0, 1, or 2 labels)
**What goes wrong:** Regex expects exactly 2 quoted labels but `terraform {}`, `locals {}`, `provider "aws" {}`, and `module "vpc" {}` have 0, 0, 1, and 1 labels respectively.
**Why it happens:** Different HCL block types have different label counts.
**How to avoid:** Make label matching optional. Build hierarchy from whatever labels are present:
  - `resource "aws_s3_bucket" "data"` -> `resource.aws_s3_bucket.data` (2 labels)
  - `module "vpc"` -> `module.vpc` (1 label)
  - `terraform` -> `terraform` (0 labels, block_type only)
  - `locals` -> `locals` (0 labels)
**Warning signs:** Test with 0-label, 1-label, and 2-label block types.

**HCL block label counts (verified):**

| Block Type | Labels | Example | Hierarchy |
|------------|--------|---------|-----------|
| `resource` | 2 | `resource "aws_s3_bucket" "data" {` | `resource.aws_s3_bucket.data` |
| `data` | 2 | `data "aws_iam_policy" "admin" {` | `data.aws_iam_policy.admin` |
| `variable` | 1 | `variable "name" {` | `variable.name` |
| `output` | 1 | `output "id" {` | `output.id` |
| `module` | 1 | `module "vpc" {` | `module.vpc` |
| `provider` | 1 | `provider "aws" {` | `provider.aws` |
| `check` | 1 | `check "health" {` | `check.health` |
| `locals` | 0 | `locals {` | `locals` |
| `terraform` | 0 | `terraform {` | `terraform` |
| `import` | 0 | `import {` | `import` |
| `moved` | 0 | `moved {` | `moved` |
| `removed` | 0 | `removed {` | `removed` |

**Confidence:** HIGH -- verified from Terraform official docs.

### Pitfall 4: Dockerfile Stage Context for Non-FROM Instructions
**What goes wrong:** A `RUN` chunk in a multi-stage build gets empty hierarchy instead of inheriting the stage name.
**Why it happens:** Each chunk is processed independently -- there's no state tracking which stage we're in.
**How to avoid:** Per CONTEXT.md: "Dockerfile non-FROM instructions inherit their stage context: stage:builder". However, since metadata extraction processes individual chunks without inter-chunk state, the approach must be:
  - `FROM golang:1.21 AS builder` -> `block_type=FROM`, `hierarchy=stage:builder`
  - `RUN go build` (in builder stage) -> `block_type=RUN`, `hierarchy=stage:builder` **only if** the chunk text contains enough context
  - **IMPORTANT LIMITATION:** If the splitter produced the RUN chunk without the preceding FROM context, we cannot determine the stage. This is Roadmap Pitfall 6.
  - **Practical approach:** For non-FROM Dockerfile instructions, set hierarchy to empty string in v1.2 (stated in REQ-10 notes: "Non-FROM instructions get empty hierarchy in v1.2"). Stage context inheritance would require inter-chunk state, which is out of scope.
**Warning signs:** Document this limitation clearly.

### Pitfall 5: Leading Whitespace in Chunk Text
**What goes wrong:** Chunk text might have leading newlines or spaces from the separator split.
**Why it happens:** The `SplitRecursively` separator patterns start with `\n`, so chunks may begin with whitespace.
**How to avoid:** Always `lstrip()` chunk text before applying regex patterns. The comment stripping function should also handle leading whitespace.
**Warning signs:** Test with chunks that have leading `\n` or spaces.

### Pitfall 6: HCL Heredoc Content Containing Block Keywords
**What goes wrong:** A heredoc like `<<EOF\nresource "fake" "example" {}\nEOF` could be split into a chunk that starts with `resource`.
**Why it happens:** The Phase 1 splitter treats `\nresource ` as a separator even inside heredocs.
**How to avoid:** This is a Phase 1 limitation (Pitfall 2 from Phase 1). The metadata extractor cannot fix this -- it will correctly extract whatever the first non-comment line shows. Accept this as a known limitation.
**Warning signs:** Rare in practice. Heredocs in Terraform typically contain shell scripts or JSON, not HCL block declarations.

### Pitfall 7: Regex Compilation on Every Call
**What goes wrong:** Calling `re.compile()` inside the extraction function means recompilation on every chunk.
**Why it happens:** Not pre-compiling regex patterns as module-level constants.
**How to avoid:** Compile ALL regex patterns at module level using `re.compile()`. This runs once at import time.
**Warning signs:** Profile if processing many chunks shows unexpectedly high CPU usage.

## Code Examples

### HCL Block Extraction Regex
```python
# Source: Terraform official docs - https://developer.hashicorp.com/terraform/language/syntax/configuration
import re

# The 12 known HCL top-level block types (same as languages.py separator)
_HCL_BLOCK_TYPES = frozenset({
    "resource", "data", "variable", "output", "locals", "module",
    "provider", "terraform", "import", "moved", "removed", "check",
})

# Match: keyword optionally followed by 1-2 quoted labels, then {
# Captures: (block_type) (optional_label1) (optional_label2)
_HCL_BLOCK_RE = re.compile(
    r'^(resource|data|variable|output|locals|module|provider|terraform|import|moved|removed|check)'
    r'(?:\s+"([^"]*)")?'   # optional first label in quotes
    r'(?:\s+"([^"]*)")?'   # optional second label in quotes
    r'\s*\{?',             # optional opening brace
)
```

### Dockerfile Instruction Extraction Regex
```python
# Source: Docker official docs - https://docs.docker.com/reference/dockerfile/

# All 18 Dockerfile instructions
_DOCKERFILE_INSTRUCTIONS = frozenset({
    "FROM", "RUN", "CMD", "LABEL", "MAINTAINER", "EXPOSE", "ENV",
    "ADD", "COPY", "ENTRYPOINT", "VOLUME", "USER", "WORKDIR",
    "ARG", "ONBUILD", "STOPSIGNAL", "HEALTHCHECK", "SHELL",
})

# Match instruction keyword at line start
_DOCKERFILE_INSTRUCTION_RE = re.compile(
    r'^(FROM|RUN|CMD|LABEL|MAINTAINER|EXPOSE|ENV|ADD|COPY|ENTRYPOINT|'
    r'VOLUME|USER|WORKDIR|ARG|ONBUILD|STOPSIGNAL|HEALTHCHECK|SHELL)\b'
)

# FROM with optional AS clause: FROM image:tag AS name
_DOCKERFILE_FROM_RE = re.compile(
    r'^FROM\s+'
    r'(?:--platform=\S+\s+)?'  # optional --platform flag
    r'(\S+)'                    # image (captures image:tag or image@digest)
    r'(?:\s+AS\s+(\S+))?'      # optional AS stage_name
    , re.IGNORECASE             # AS can be lowercase per Docker spec
)
```

### Bash Function Extraction Regex
```python
# Source: Bash reference - https://linuxvox.com/blog/what-are-the-parentheses-used-for-in-a-bash-shell-script-function-definition-like-f/

# Three function definition patterns:
# 1. POSIX: name() { ... }
# 2. ksh:   function name { ... }
# 3. hybrid: function name() { ... }
_BASH_FUNCTION_RE = re.compile(
    r'^(?:'
    r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(\s*\))?\s*\{?'  # function keyword form
    r'|'
    r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)\s*\{?'                  # POSIX name() form
    r')'
)
```

### DevOpsMetadata Dataclass
```python
import dataclasses

@dataclasses.dataclass
class DevOpsMetadata:
    """Structured metadata for a DevOps file chunk.

    Fields:
        block_type: The type of block (e.g., "resource", "FROM", "function").
                    Empty string for non-DevOps or unrecognized chunks.
        hierarchy: Dot-separated hierarchy for HCL (e.g., "resource.aws_s3_bucket.data"),
                   colon-prefixed for Dockerfile/Bash (e.g., "stage:builder", "function:deploy").
                   Empty string for non-DevOps or unrecognized chunks.
        language_id: Language identifier ("hcl", "dockerfile", "bash").
                     Empty string for non-DevOps files.
    """
    block_type: str
    hierarchy: str
    language_id: str
```

### Main Dispatch Function
```python
# Language routing map: language identifiers from extract_language() -> extraction function
# "tf", "tfvars", "hcl" all route to HCL extraction
# "dockerfile" routes to Dockerfile extraction
# "sh", "bash", "zsh", "shell" all route to Bash extraction
_LANGUAGE_DISPATCH = {
    "hcl": extract_hcl_metadata,
    "tf": extract_hcl_metadata,
    "tfvars": extract_hcl_metadata,
    "dockerfile": extract_dockerfile_metadata,
    "sh": extract_bash_metadata,
    "bash": extract_bash_metadata,
    "zsh": extract_bash_metadata,
    "shell": extract_bash_metadata,
}

_LANGUAGE_ID_MAP = {
    "hcl": "hcl", "tf": "hcl", "tfvars": "hcl",
    "dockerfile": "dockerfile",
    "sh": "bash", "bash": "bash", "zsh": "bash", "shell": "bash",
}

_EMPTY_METADATA = DevOpsMetadata(block_type="", hierarchy="", language_id="")

@cocoindex.op.function()
def extract_devops_metadata(text: str, language: str) -> DevOpsMetadata:
    """Extract metadata from a DevOps chunk.

    Args:
        text: The chunk text content.
        language: Language identifier from extract_language() (e.g., "tf", "dockerfile", "sh").

    Returns:
        DevOpsMetadata with extracted or empty-string fields.
    """
    extractor = _LANGUAGE_DISPATCH.get(language)
    if extractor is None:
        return _EMPTY_METADATA

    metadata = extractor(text)
    # Always set language_id for known DevOps files, even if block_type/hierarchy are empty
    return DevOpsMetadata(
        block_type=metadata.block_type,
        hierarchy=metadata.hierarchy,
        language_id=_LANGUAGE_ID_MAP[language],
    )
```

### How This Gets Used in Flow (Phase 3 -- for context only)
```python
# Phase 3 will add this to flow.py, after chunking:
with file["chunks"].row() as chunk:
    chunk["metadata"] = chunk["text"].transform(
        extract_devops_metadata,
        language=file["extension"],  # "extension" field holds language from extract_language
    )
    # Then collect metadata fields:
    code_embeddings.collect(
        filename=file["filename"],
        location=chunk["location"],
        embedding=chunk["embedding"],
        block_type=chunk["metadata"]["block_type"],
        hierarchy=chunk["metadata"]["hierarchy"],
        language_id=chunk["metadata"]["language_id"],
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `extract_extension` function | `extract_language` with filename pattern routing | Phase 1 (v1.2) | Dockerfile/Containerfile now correctly identified |
| No metadata on chunks | `DevOpsMetadata` dataclass per chunk | Phase 2 (v1.2) | Enables structured search and filtering |

**Deprecated/outdated:**
- None -- this is new functionality.

## Chunk Text Format Analysis

Understanding what chunk text looks like after `SplitRecursively` is critical for regex design.

### How Separators Produce Chunks

The Phase 1 separators all start with `\n`:
- HCL: `\n(?:resource|data|...)` -- splits before the keyword
- Dockerfile: `\nFROM `, `\n(?:RUN|COPY|...)` -- splits before the instruction
- Bash: `\nfunction ` -- splits before the `function` keyword

After splitting, the separator text (including `\n` and the keyword) is included at the **start** of the subsequent chunk. This means:

| Language | Separator | Chunk starts with |
|----------|-----------|-------------------|
| HCL | `\nresource ` | `resource "type" "name" {` (with possible leading `\n`) |
| Dockerfile | `\nFROM ` | `FROM image:tag AS name` (with possible leading `\n`) |
| Dockerfile | `\nRUN ` | `RUN command` (with possible leading `\n`) |
| Bash | `\nfunction ` | `function name() {` (with possible leading `\n`) |
| Bash | (blank line) | `name() {` (POSIX functions split by Level 2) |

**Critical implication:** Always `lstrip()` the chunk text before regex matching to handle the leading newline from the separator.

**Confidence:** MEDIUM -- based on standard recursive text splitting behavior (separator kept at start of next chunk). Not explicitly confirmed in CocoIndex docs. The regex should handle both cases (with or without leading whitespace) via `lstrip()`.

## HCL Block Types Reference

Complete list of 12 top-level HCL block types with their label structure:

| Block Type | Label Count | Labels | Added In |
|------------|-------------|--------|----------|
| `resource` | 2 | type, name | Original |
| `data` | 2 | type, name | Original |
| `variable` | 1 | name | Original |
| `output` | 1 | name | Original |
| `module` | 1 | name | Original |
| `provider` | 1 | type | Original |
| `check` | 1 | name | Terraform 1.5 |
| `locals` | 0 | (none) | Original |
| `terraform` | 0 | (none) | Original |
| `import` | 0 | (none) | Terraform 1.5 |
| `moved` | 0 | (none) | Terraform 1.1 |
| `removed` | 0 | (none) | Terraform 1.7 |

**Confidence:** HIGH -- verified from Terraform official documentation.

## Dockerfile Instructions Reference

All 18 Dockerfile instructions with their metadata extraction behavior:

| Instruction | Has Stage Context | Hierarchy Format |
|-------------|-------------------|------------------|
| `FROM` | Yes (defines stage) | `stage:name` or `image:image_ref` |
| `RUN` | No (in v1.2) | `""` |
| `CMD` | No | `""` |
| `ENTRYPOINT` | No | `""` |
| `COPY` | No | `""` |
| `ADD` | No | `""` |
| `ENV` | No | `""` |
| `EXPOSE` | No | `""` |
| `VOLUME` | No | `""` |
| `WORKDIR` | No | `""` |
| `USER` | No | `""` |
| `LABEL` | No | `""` |
| `ARG` | No | `""` |
| `ONBUILD` | No | `""` |
| `STOPSIGNAL` | No | `""` |
| `HEALTHCHECK` | No | `""` |
| `SHELL` | No | `""` |
| `MAINTAINER` | No (deprecated) | `""` |

**Confidence:** HIGH -- verified from Docker official documentation.

## Bash Function Patterns Reference

Three recognized function definition syntaxes:

| Syntax | Example | Standards |
|--------|---------|-----------|
| POSIX | `deploy_app() { ... }` | POSIX, all shells |
| ksh-style | `function deploy_app { ... }` | ksh, bash |
| Hybrid | `function deploy_app() { ... }` | bash only |

All three should produce: `block_type="function"`, `hierarchy="function:deploy_app"`.

Non-function Bash chunks (top-level code, control flow) get: `block_type=""`, `hierarchy=""`.

**Confidence:** HIGH -- verified from Bash documentation and POSIX standard references.

## Open Questions

1. **Separator placement in chunk text**
   - What we know: Standard recursive text splitters keep separators at the start of the next chunk. CocoIndex follows this pattern based on analogous behavior.
   - What's unclear: CocoIndex docs do not explicitly document whether the separator is kept or removed from chunks.
   - Recommendation: Use `lstrip()` + regex that matches the keyword at the start. This handles both "separator kept" and "separator stripped" scenarios. Tests should include chunks with and without leading whitespace.

2. **Chunk overlap and duplicate metadata**
   - What we know: Phase 1 uses `chunk_overlap=300` bytes. Overlapping text could contain block starts from adjacent chunks.
   - What's unclear: Whether overlapping portions get their own chunks or are only included as trailing/leading content.
   - Recommendation: Since we only match at the start of the chunk (after stripping), overlapping keywords at the end of a chunk are safely ignored. No action needed.

3. **Dockerfile `FROM` without stage name**
   - What we know: CONTEXT.md says "Dockerfile FROM without AS uses image name: `image:ubuntu:22.04`"
   - What's unclear: For `FROM golang:1.21` (no AS), the hierarchy would be `image:golang:1.21` which contains nested colons.
   - Recommendation: Accept nested colons. The format `image:golang:1.21` is unambiguous because the prefix is always `image:` or `stage:`.

## Testing Strategy

Since this module is standalone (no CocoIndex runtime needed for testing), tests should:

1. **Test per-language functions directly** -- no `@cocoindex.op.function()` needed in unit tests
2. **Follow existing test structure** -- `tests/indexer/test_metadata.py` with class-based grouping
3. **Test from CONTEXT.md success criteria** -- the 5 scenarios are exact test cases
4. **Cover edge cases** per pitfall section above

Test file location: `tests/indexer/test_metadata.py`

```python
# Example test structure (following existing conventions)
class TestExtractHclMetadata:
    def test_resource_two_labels(self): ...
    def test_module_one_label(self): ...
    def test_terraform_no_labels(self): ...
    def test_comment_before_block(self): ...

class TestExtractDockerfileMetadata:
    def test_from_with_as(self): ...
    def test_from_without_as(self): ...
    def test_run_instruction(self): ...

class TestExtractBashMetadata:
    def test_posix_function(self): ...
    def test_ksh_function(self): ...
    def test_non_function_chunk(self): ...

class TestExtractDevopsMetadata:
    def test_python_file_empty_strings(self): ...
    def test_hcl_always_has_language_id(self): ...
```

## Sources

### Primary (HIGH confidence)
- [Terraform Configuration Syntax](https://developer.hashicorp.com/terraform/language/syntax/configuration) -- HCL block types, label counts, syntax
- [Terraform `check` Block Reference](https://developer.hashicorp.com/terraform/language/block/check) -- check block syntax and labels
- [Dockerfile Reference](https://docs.docker.com/reference/dockerfile/) -- All 18 instructions, FROM AS syntax
- [CocoIndex Custom Functions](https://cocoindex.io/docs/custom_ops/custom_functions) -- @cocoindex.op.function() with dataclass return
- [CocoIndex Data Types](https://cocoindex.io/docs/core/data_types) -- Struct type supports dataclass, NamedTuple, Pydantic
- [CocoIndex Functions](https://cocoindex.io/docs/ops/functions) -- SplitRecursively output format (KTable with text, location fields)

### Secondary (MEDIUM confidence)
- [Bash Function Definitions](https://linuxvox.com/blog/what-are-the-parentheses-used-for-in-a-bash-shell-script-function-definition-like-f/) -- Three function syntax forms
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) -- Function definition conventions
- [CocoIndex Academic Papers Example](https://cocoindex.io/docs/examples/academic_papers_index) -- Dataclass return from op.function pattern

### Tertiary (LOW confidence)
- Separator placement in chunks: inferred from LangChain `RecursiveCharacterTextSplitter` behavior (keep_separator defaults to start). Not confirmed from CocoIndex docs specifically.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, confirmed CocoIndex dataclass support
- Architecture: HIGH -- follows existing codebase patterns, CONTEXT.md decisions are clear
- Regex patterns: HIGH -- HCL/Dockerfile syntax verified from official docs
- Pitfalls: HIGH -- well-characterized from roadmap and syntax analysis
- Chunk text format: MEDIUM -- separator placement inferred, not confirmed from CocoIndex docs

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (stable -- Python stdlib, mature Terraform/Docker syntax)
