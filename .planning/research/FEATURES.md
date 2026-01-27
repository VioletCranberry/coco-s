# Feature Landscape: DevOps Language Support (v1.2)

**Domain:** DevOps language-aware code search -- HCL (Terraform), Dockerfile, Bash/Shell
**Researched:** 2026-01-27
**Confidence:** HIGH (verified against CocoIndex API, Tree-sitter grammars, official Terraform/Docker/Bash documentation)

## Table Stakes

Features users expect when a code search tool claims "DevOps language support." Missing any of these makes the feature feel incomplete or broken.

### Chunking Features

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **HCL block-level chunking** | Terraform users think in blocks (resource, module, variable). Splitting mid-block destroys the semantic unit. | MEDIUM | Use `CustomLanguageSpec` with regex separators at block boundaries (`resource`, `data`, `module`, `variable`, `output`, `locals`, `provider`, `terraform`). HCL is NOT in CocoIndex's built-in Tree-sitter list -- custom_languages is required. |
| **Dockerfile instruction-level chunking** | Dockerfiles are sequential instruction lists. A chunk that starts mid-RUN command is useless. FROM boundaries are critical for multi-stage builds. | MEDIUM | Use `CustomLanguageSpec` with FROM as Level 1 separator (stage boundary), then major instructions (RUN, COPY, ENV, etc.) as Level 2. Dockerfile is NOT in CocoIndex's built-in Tree-sitter list. |
| **Bash function-level chunking** | Shell scripts organize logic into functions. Users search for "the deployment function" or "the cleanup script." | LOW-MEDIUM | Bash IS in CocoIndex's built-in Tree-sitter list, so the existing chunking already understands function boundaries. Custom regex is only needed if Tree-sitter's bash chunking proves inadequate at separating logical script sections. Test first. |
| **File pattern recognition** | Indexing must actually pick up DevOps files. Users expect `*.tf`, `Dockerfile`, `*.sh` to be indexed without manual configuration. | LOW | Add patterns to `IndexingConfig.include_patterns`. Must handle: `*.tf`, `*.hcl`, `*.tfvars`, `Dockerfile`, `Dockerfile.*`, `Containerfile`, `*.sh`, `*.bash`. |
| **Correct language routing** | When a `.tf` file is chunked, it must use HCL separators, not plain text fallback. When a `.sh` file is chunked, it should use Bash rules. | LOW | CocoIndex's `language` parameter receives the file extension. Custom language `aliases` must include all relevant extensions. Special case: Dockerfile has no extension -- need filename-based routing. |
| **Non-DevOps files unaffected** | Adding DevOps support must not break existing Python/JS/Rust chunking. The 30+ Tree-sitter languages must continue working identically. | LOW | `custom_languages` only activates for extensions/names that match custom specs. Built-in Tree-sitter languages take priority (verified from CocoIndex docs). Risk: Bash name collision between custom and built-in. |

### Metadata Features

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **HCL block type identification** | A search result showing `resource "aws_s3_bucket" "data"` should indicate this is a "resource" block. Without this, DevOps search results are no better than grep. | LOW | Regex extraction from chunk text: match `^(resource\|data\|variable\|...)` at chunk start. 12 known top-level block types in Terraform. |
| **Dockerfile instruction type** | Users need to know whether a search result is a FROM, RUN, COPY, or ENV instruction. Critical for understanding build flow. | LOW | First keyword of each instruction is the type. Regex: `^(FROM\|RUN\|COPY\|...)`. |
| **Bash function name** | When searching for "database backup," the result should show it found `function backup_database()`. | LOW | Regex match for `function_name()` or `function func_name` patterns. |
| **File path and line numbers** | Already a v1.0 feature. DevOps files must work identically to programming language files for navigation. | NONE | Already implemented. No changes needed. |
| **Relevance scores** | Already a v1.0 feature. Cosine similarity scores must work with DevOps file embeddings. | NONE | Already implemented. Embedding model is language-agnostic. |

### Search Features

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Language filter for DevOps files** | `--language terraform` or `--language dockerfile` should narrow results to those file types only. | LOW | Extend `LANGUAGE_EXTENSIONS` mapping in `query.py` with `"terraform": [".tf", ".hcl", ".tfvars"]`, `"dockerfile": ["Dockerfile"]`, `"bash": [".sh", ".bash"]`. Dockerfile is special -- match on basename, not extension. |
| **Mixed codebase search** | A repo with both Python and Terraform should return results from both. DevOps files should not require a separate index. | LOW | Single flow with `custom_languages` handles this. All files go through the same pipeline. Already confirmed in architecture research. |
| **Search results include content** | DevOps file chunks must be readable in search output, with proper syntax highlighting for HCL, Dockerfile, and Bash. | LOW | Add to `EXTENSION_LANG_MAP` in `formatter.py`: `"tf": "hcl"`, `"hcl": "hcl"`, `"Dockerfile": "dockerfile"` (Rich library supports these). Verify Rich supports `hcl` and `dockerfile` syntax themes. |


## Differentiators

Features that make CocoSearch meaningfully better than grep/ripgrep for DevOps file search. These are not expected but highly valued.

### Metadata Enrichment (Primary Differentiator)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **HCL resource hierarchy** | Show `resource.aws_s3_bucket.data` or `module.vpc > resource.aws_subnet.public` in results. Grep shows raw text; CocoSearch shows structural context. | MEDIUM | Extract from block labels. Two-label blocks (resource, data) produce `type.resource_type.name`. Single-label blocks (variable, output) produce `type.name`. Nested hierarchy (module composition) requires parent tracking -- defer nested modules to future. |
| **Dockerfile build stage context** | Show `stage:builder` or `stage:production` alongside instruction results. A RUN chunk in a multi-stage Dockerfile is meaningless without knowing which stage it belongs to. | MEDIUM | Parse FROM...AS name to identify stages. Track "current stage" context for subsequent instructions. Requires looking at preceding FROM in the file, not just the chunk. This is the hardest metadata to extract from a chunk alone -- may need file-level pre-processing. |
| **Terraform provider context** | Show which provider/cloud a resource belongs to (e.g., AWS, GCP, Azure). Useful in multi-cloud repos where "find the load balancer" could match AWS ALB or GCP LB. | LOW | Infer from resource type prefix: `aws_` = AWS, `azurerm_` = Azure, `google_` = GCP, `kubernetes_` = Kubernetes. Heuristic but reliable for 95%+ of Terraform code. |
| **Bash script purpose annotation** | Annotate chunks with contextual purpose: "CI/CD script" (from path like `ci/`, `.github/`), "deployment function" (from function name), "entrypoint" (from common patterns like `main()` or `"$@"`). | MEDIUM | Path-based heuristics plus content-based keyword matching. Less precise than HCL/Dockerfile structure, but still adds value over raw grep. |
| **Block type search filter** | `--block-type resource` to search only Terraform resources, or `--block-type function` to search only Bash functions. No existing tool offers this granularity for DevOps files. | LOW | SQL WHERE clause on `block_type` column. Requires metadata extraction to populate the column. Trivial once metadata is stored. |
| **Hierarchy search filter** | `--hierarchy "aws_s3"` to find all S3-related resources, or `--hierarchy "stage:build"` to find all build stage instructions. Enables precise infrastructure navigation. | LOW | SQL WHERE with LIKE/ILIKE on `hierarchy` column. Trivial once metadata is stored. |

### Chunking Quality (Secondary Differentiator)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **HCL nested block preservation** | Keep `lifecycle`, `ingress`, `egress`, `provisioner` blocks intact within their parent resource block. Splitting a `lifecycle` block from its `aws_instance` resource loses critical context. | MEDIUM | Regex separator hierarchy: Level 1 = top-level blocks, Level 2 = nested blocks. CocoIndex's `SplitRecursively` tries higher-level separators first, falling to lower levels only if chunks exceed `chunk_size`. Large resource blocks may still split at nested block boundaries, which is the correct behavior. |
| **Dockerfile RUN command grouping** | Multi-line RUN commands (with `\` continuation) should be kept as one chunk. A 15-line `RUN apt-get install && pip install ...` command is a single semantic unit. | LOW | Regex separator pattern should NOT split on continuation lines. The instruction-level separator `\n(?=RUN\s)` only matches the start of a new instruction, preserving multi-line commands. |
| **Bash heredoc preservation** | Heredocs (`<<EOF ... EOF`) are common in deployment scripts. Splitting mid-heredoc produces nonsensical chunks. | LOW | Tree-sitter's built-in bash parser understands heredocs as `heredoc_redirect` nodes. If using custom regex, heredoc boundaries are harder to capture. This favors keeping Tree-sitter's built-in bash support over custom regex. |
| **Comment block association** | Comments preceding a Terraform resource or Bash function should be included in the same chunk. They provide the "why" that makes the code searchable. | LOW | SplitRecursively's natural behavior: comments immediately before a block will be included in the chunk below (since the separator triggers at block start). No special handling needed. |


## Anti-Features

Features that seem useful but should be deliberately NOT built. Building these would add complexity without proportionate value, or would violate CocoSearch's architecture.

| Anti-Feature | Why It Seems Useful | Why Problematic | What to Do Instead |
|--------------|--------------------|-----------------|--------------------|
| **Terraform plan/state integration** | "Show what resources actually exist in the cloud alongside the code" | Requires cloud credentials, API calls, state file access. Completely out of scope for a local code search tool. Violates local-first principle. | Search code only. Let users correlate with their own `terraform state list` output. |
| **Dockerfile build graph analysis** | "Show the dependency graph between build stages" | Requires parsing COPY --from= references, resolving stage names, building a graph. This is a build tool feature, not a search feature. | Extract stage names as metadata. Let the calling LLM (Claude) reason about stage dependencies from the chunks returned. |
| **Bash script execution analysis** | "Track variable values through script execution" | Bash is dynamically scoped and uses eval, source, etc. Static analysis is brittle. ShellCheck exists for this. | Extract function boundaries and names. Let semantic search handle "what does this script do?" queries via embedding similarity. |
| **HCL module resolution** | "Resolve `source = "./modules/vpc"` and inline the module contents" | Requires filesystem traversal, registry downloads, variable substitution. This is `terraform init` territory. | Index each .tf file independently. The module path appears in the file and is searchable. Users can follow module references manually. |
| **Custom Tree-sitter grammars** | "Ship tree-sitter-hcl and tree-sitter-dockerfile for native AST parsing" | CocoIndex's SplitRecursively uses its own bundled Tree-sitter. Adding custom grammars would require either (a) forking CocoIndex or (b) a separate parsing step. Massive complexity increase for marginal improvement over regex separators. | Use CocoIndex's `custom_languages` with regex separators. For HCL and Dockerfile, the structure is regular enough that regex works well. Block-level chunking does not require full AST parsing. |
| **Secrets detection in DevOps files** | "Flag potential secrets in .tf files or shell scripts" | Adds security scanning scope. Tools like `tfsec`, `checkov`, `gitleaks` exist for this. Not a search feature. | Out of scope. Users should run dedicated security tools. |
| **Terraform version-specific parsing** | "Handle HCL1 vs HCL2 syntax differences" | HCL1 is deprecated since Terraform 0.12 (2019). No one writes new HCL1 code. Supporting it doubles parsing complexity for near-zero users. | Support HCL2 only. HCL1 files will still be indexed as plain text if encountered. |
| **YAML/JSON Terraform support** | "Some Terraform configs use JSON format instead of HCL" | JSON Terraform files are extremely rare in practice. YAML is already supported via built-in Tree-sitter. Adding JSON-Terraform-specific metadata extraction for a tiny edge case is not worth it. | JSON files are already indexed as JSON. YAML files already indexed as YAML. They just lack Terraform-specific metadata, which is acceptable. |
| **Dockerfile linting integration** | "Highlight Dockerfile best practice violations in search results" | Not a search feature. `hadolint` exists for this purpose. Mixing linting with search muddles both. | Return raw chunks. Let the calling LLM identify best practice issues if asked. |
| **Shell dialect detection** | "Distinguish bash from zsh from sh from fish" | File extension already provides this signal. The structural differences between bash/zsh/sh are minimal for chunking purposes. Fish has a different syntax but is rarely used in DevOps. | Treat all `*.sh`, `*.bash`, `*.zsh` identically for chunking. Use extension for language_id metadata. |


## Feature Dependencies

```
[DevOps Chunking Layer]
CustomLanguageSpec definitions (HCL, Dockerfile, Bash)
    |
    +--> SplitRecursively integration (pass custom_languages)
    |       |
    |       +--> File pattern recognition (*.tf, Dockerfile, *.sh added to config)
    |
    +--> Language routing verification (extension -> correct language spec)

[Metadata Layer] (depends on chunking)
Metadata extraction function (extract_devops_metadata)
    |
    +--> HCL block type + hierarchy extraction (regex on chunk text)
    |
    +--> Dockerfile instruction type + stage extraction (regex on chunk text)
    |
    +--> Bash function name extraction (regex on chunk text)
    |
    +--> Flow integration (metadata fields added to collector)
         |
         +--> Schema extension (3 new TEXT columns in PostgreSQL)

[Search Layer] (depends on metadata)
SearchResult field extension (block_type, hierarchy, language_id)
    |
    +--> SQL query update (SELECT new columns)
    |
    +--> Language filter extension (terraform, dockerfile, bash)
    |
    +--> Formatter update (show metadata in JSON and pretty output)
    |
    +--> MCP server update (include metadata in search_code response)
    |
    +--> Graceful degradation (fall back for pre-v1.2 indexes)

[Enhancement Layer] (depends on search, optional)
Block type filter (--block-type resource)
    |
    +--> Hierarchy filter (--hierarchy "aws_s3")
    |
    +--> Provider inference (aws_, azurerm_, google_ prefix heuristic)
```

### Dependency Notes

- **Chunking must come first.** Without correct chunk boundaries, metadata extraction produces garbage (a chunk that starts mid-resource-block cannot identify its block type).
- **Metadata extraction depends on chunking quality.** The regex patterns match the START of a chunk. If SplitRecursively produces chunks that start at block boundaries (as designed), regex works. If chunks start mid-block, regex fails silently (returns empty metadata).
- **Search changes are backward-compatible.** New columns use COALESCE with empty string defaults. Pre-v1.2 indexes degrade gracefully (no metadata, but search still works).
- **Block type and hierarchy filters are optional enhancements.** Basic search works without them. They add precision filtering for power users.


## Per-Language Metadata Specification

### HCL (Terraform)

**Chunk boundaries:** Top-level block start (`resource`, `data`, `variable`, `output`, `locals`, `module`, `provider`, `terraform`, `import`, `moved`, `removed`, `check`).

**Metadata extracted per chunk:**

| Field | Example Value | Extraction Method |
|-------|--------------|-------------------|
| `block_type` | `"resource"` | First keyword in block declaration |
| `hierarchy` | `"resource.aws_s3_bucket.data"` | `block_type.label1.label2` from block declaration |
| `language_id` | `"hcl"` | File extension (`.tf`, `.hcl`, `.tfvars`) |

**HCL block label patterns:**

| Block Type | Labels | Hierarchy Format | Example |
|------------|--------|-----------------|---------|
| `resource` | 2 (type, name) | `resource.TYPE.NAME` | `resource.aws_s3_bucket.data` |
| `data` | 2 (type, name) | `data.TYPE.NAME` | `data.aws_ami.ubuntu` |
| `module` | 1 (name) | `module.NAME` | `module.vpc` |
| `variable` | 1 (name) | `variable.NAME` | `variable.region` |
| `output` | 1 (name) | `output.NAME` | `output.bucket_arn` |
| `provider` | 1 (name) | `provider.NAME` | `provider.aws` |
| `locals` | 0 | `locals` | `locals` |
| `terraform` | 0 | `terraform` | `terraform` |
| `import` | 0 | `import` | `import` |
| `moved` | 0 | `moved` | `moved` |
| `removed` | 0 | `removed` | `removed` |
| `check` | 1 (name) | `check.NAME` | `check.health` |

**Provider inference (optional enrichment):**

| Resource Prefix | Provider | Cloud |
|----------------|----------|-------|
| `aws_` | AWS | Amazon Web Services |
| `azurerm_` | Azure | Microsoft Azure |
| `google_` | GCP | Google Cloud Platform |
| `kubernetes_` | Kubernetes | Container orchestration |
| `helm_` | Helm | Kubernetes package manager |
| `github_` | GitHub | Version control |
| `docker_` | Docker | Container runtime |
| `null_` | Null | Utility provider |
| `random_` | Random | Utility provider |
| `local_` | Local | Utility provider |
| `tls_` | TLS | Certificate management |

### Dockerfile

**Chunk boundaries:** FROM instruction (build stage boundary), then individual instructions.

**Metadata extracted per chunk:**

| Field | Example Value | Extraction Method |
|-------|--------------|-------------------|
| `block_type` | `"FROM"`, `"RUN"`, `"COPY"` | First keyword of the instruction |
| `hierarchy` | `"stage:builder"`, `"stage:production"` | FROM...AS name; instructions inherit stage |
| `language_id` | `"dockerfile"` | Filename-based (`Dockerfile*`, `Containerfile`) |

**Dockerfile instruction types (all 19):**

| Instruction | Frequency | Metadata Value | Notes |
|------------|-----------|----------------|-------|
| `FROM` | Every file | Stage boundary | Always has base image; optionally `AS name` |
| `RUN` | Very common | Build command | Often multi-line with `\` continuation or heredoc |
| `COPY` | Very common | File transfer | May have `--from=stage` for multi-stage |
| `ENV` | Common | Environment setup | Key=value pairs |
| `WORKDIR` | Common | Directory context | Sets working directory |
| `EXPOSE` | Common | Port declaration | Metadata only, does not publish |
| `CMD` | Once per file | Runtime command | Final command |
| `ENTRYPOINT` | Once per file | Runtime entrypoint | Often combined with CMD |
| `ARG` | Common | Build argument | Available only during build |
| `ADD` | Less common | File transfer with extras | Like COPY but can extract archives and fetch URLs |
| `LABEL` | Less common | Image metadata | Key=value metadata pairs |
| `VOLUME` | Less common | Mount point | Declares volumes |
| `USER` | Less common | User context | Sets runtime user |
| `HEALTHCHECK` | Less common | Health monitoring | Container health check config |
| `SHELL` | Rare | Shell override | Changes default shell |
| `ONBUILD` | Rare | Trigger | Deferred instruction |
| `STOPSIGNAL` | Rare | Signal config | Container stop signal |
| `MAINTAINER` | Deprecated | Author info | Use LABEL instead |
| `CROSS_BUILD` | Rare | Cross-compilation | Platform-specific |

**Stage tracking challenge:** A Dockerfile chunk containing a RUN instruction should ideally know which build stage it belongs to (e.g., `stage:builder`). However, chunks are processed independently. Solution: the metadata extractor must be file-aware, not just chunk-aware. Two approaches:
1. **Simple (recommended):** Extract stage from chunk text only. FROM chunks get stage names. Other instructions get empty hierarchy unless the FROM is in the same chunk.
2. **Complex (deferred):** Pre-process the file to build a stage map, then annotate each chunk with its parent stage. This requires two-pass processing.

Recommend the simple approach for v1.2. Stage context for non-FROM chunks is a v1.3 enhancement.

### Bash/Shell

**Chunk boundaries:** Function definitions, major control flow (if/for/while/case), blank lines between logical sections.

**Metadata extracted per chunk:**

| Field | Example Value | Extraction Method |
|-------|--------------|-------------------|
| `block_type` | `"function"`, `"script"` | Function definition pattern match |
| `hierarchy` | `"function:deploy_app"`, `"function:cleanup"` | Function name extraction |
| `language_id` | `"bash"` | File extension (`.sh`, `.bash`, `.zsh`) |

**Bash structural elements:**

| Element | Frequency | Metadata Value | Notes |
|---------|-----------|----------------|-------|
| `function name() { }` | Common | `function:name` | Standard function definition |
| `function name { }` | Common | `function:name` | Alternative syntax (no parens) |
| `if/elif/else/fi` | Common | `"script"` (no hierarchy) | Control flow, not a named unit |
| `for/while/until` | Common | `"script"` (no hierarchy) | Loop, not a named unit |
| `case/esac` | Common | `"script"` (no hierarchy) | Pattern matching |
| Top-level commands | Always | `"script"` (no hierarchy) | Sequential commands outside functions |
| Shebang (`#!/bin/bash`) | Usually first line | Part of first chunk | Identifies interpreter |

**Special consideration:** Many DevOps bash scripts are "flat" -- no functions, just a sequence of commands with comments as section separators. For these scripts, the most meaningful metadata is the filename/path itself (e.g., `scripts/deploy.sh`) rather than internal structure. The `block_type="script"` with empty hierarchy is the correct representation.


## Search Filter Specification

### Existing Filters (v1.0, unchanged)

| Filter | Parameter | Values | Example |
|--------|-----------|--------|---------|
| Language | `--language` / `language` | python, javascript, typescript, etc. | `--language python` |
| Result limit | `--limit` / `limit` | integer | `--limit 5` |
| Min score | `--min-score` | 0.0-1.0 | `--min-score 0.5` |

### New Language Filter Values (v1.2)

| Value | Matches Files | Extension Patterns |
|-------|--------------|-------------------|
| `terraform` or `hcl` | `*.tf`, `*.hcl`, `*.tfvars` | `%.tf`, `%.hcl`, `%.tfvars` |
| `dockerfile` | `Dockerfile`, `Dockerfile.*`, `Containerfile` | Special: basename LIKE pattern |
| `bash` or `shell` | `*.sh`, `*.bash`, `*.zsh` | `%.sh`, `%.bash`, `%.zsh` |

**Dockerfile filter challenge:** Dockerfiles often have no extension (just `Dockerfile`) or variant names (`Dockerfile.production`, `Dockerfile.dev`). The existing language filter uses `filename LIKE %s` patterns with extensions. Dockerfile filtering needs `filename LIKE '%/Dockerfile%'` or `basename(filename) LIKE 'Dockerfile%'`. This requires SQL changes -- PostgreSQL does not have a native basename function, but `filename LIKE '%Dockerfile%' OR filename LIKE '%Containerfile%'` works for practical cases.

### New Metadata Filters (v1.2, optional enhancement)

| Filter | Parameter | Values | Example |
|--------|-----------|--------|---------|
| Block type | `--block-type` | resource, data, module, variable, output, FROM, RUN, function, script | `--block-type resource` |
| Hierarchy | `--hierarchy` | partial match on hierarchy string | `--hierarchy aws_s3` |

These filters are additive (AND) with the existing language filter. Combining `--language terraform --block-type resource --hierarchy aws_s3` narrows results to only S3 resource blocks in Terraform files.


## MVP Recommendation for v1.2

### Must Ship (Core Deliverable)

1. **Custom language definitions** for HCL, Dockerfile, Bash -- without these, DevOps files are indexed as plain text (broken)
2. **File pattern additions** to IndexingConfig -- without these, DevOps files are not picked up at all
3. **Block type metadata extraction** -- the minimum viable "DevOps awareness"
4. **Language filter additions** for terraform, dockerfile, bash -- users need to narrow search scope
5. **Search result metadata in output** -- surface block_type, hierarchy, language_id in JSON and pretty formats
6. **MCP server metadata** -- calling LLMs need structured metadata for better synthesis

### Should Ship (Significant Value Add)

7. **HCL hierarchy extraction** (resource.aws_s3_bucket.data) -- transforms search from "here's some HCL" to "here's the S3 bucket resource named data"
8. **Bash function name extraction** -- names are the most searchable unit in shell scripts
9. **Graceful degradation** for pre-v1.2 indexes -- users should not be forced to re-index everything
10. **Syntax highlighting** for DevOps files in pretty output -- visual quality matters

### Defer to v1.3 (Post-Validation)

11. **Dockerfile stage tracking** for non-FROM instructions -- requires two-pass or file-level context
12. **Block type search filter** (`--block-type`) -- useful but not critical for initial release
13. **Hierarchy search filter** (`--hierarchy`) -- power user feature, validate demand first
14. **Provider inference** for Terraform resources -- nice annotation but not essential
15. **Bash script purpose annotation** -- heuristic-based, may not be reliable enough


## Competitive Positioning

| Capability | grep/ripgrep | Sourcegraph | GitHub Code Search | CocoSearch v1.2 |
|-----------|-------------|-------------|-------------------|----------------|
| Find DevOps files | Yes (patterns) | Yes | Yes | Yes |
| Semantic search ("find the S3 bucket config") | No | Yes (Deep Search) | Limited | Yes |
| Block type identification | No | No (generic AST) | No | **Yes** |
| Resource hierarchy in results | No | No | No | **Yes** |
| Build stage context | No | No | No | **Yes** (FROM only in v1.2) |
| Fully local / private | Yes | Enterprise only | No (cloud) | **Yes** |
| Filter by block type | No | No | No | **Planned v1.3** |
| Mixed codebase search | Yes | Yes | Yes | Yes |
| Incremental indexing | N/A | Yes | Yes | Yes (CocoIndex) |
| MCP integration | No | Yes (MCP server) | No | **Yes** |

**Key differentiator:** CocoSearch v1.2 is the only tool that combines semantic search with DevOps-specific metadata (block types, resource hierarchy) in a fully local, privacy-preserving package. grep finds text but lacks semantics. Sourcegraph has semantics but lacks DevOps-specific structural awareness and requires cloud/enterprise infrastructure. CocoSearch v1.2 fills the gap.


## User Query Examples (What People Actually Search For)

These queries illustrate why DevOps-specific metadata matters:

| Natural Language Query | Without Metadata | With v1.2 Metadata |
|-----------------------|-----------------|-------------------|
| "S3 bucket configuration" | Returns chunks from .tf files with matching text | Returns chunks annotated with `block_type=resource`, `hierarchy=resource.aws_s3_bucket.*` |
| "Docker build stage for production" | Returns FROM lines in Dockerfiles | Returns FROM chunk with `hierarchy=stage:production` |
| "deployment function in shell scripts" | Returns text-similar chunks from .sh files | Returns chunk with `block_type=function`, `hierarchy=function:deploy` |
| "VPC module" | Returns chunks mentioning VPC | Returns chunk with `block_type=module`, `hierarchy=module.vpc` |
| "environment variables in Docker" | Returns ENV instructions and text mentioning env | Returns ENV instructions with `block_type=ENV`, `language_id=dockerfile` |
| "database connection settings" | Returns various chunks across all files | Metadata helps the calling LLM distinguish Terraform data source vs. application config vs. Docker ENV |


## Sources

**CocoIndex (Verified - HIGH confidence):**
- [CocoIndex Functions Documentation](https://cocoindex.io/docs/ops/functions) -- SplitRecursively API, CustomLanguageSpec structure, supported languages list
- [CocoIndex Academic Papers Example](https://cocoindex.io/docs/examples/academic_papers_index) -- CustomLanguageSpec usage pattern
- CocoIndex Python API (`cocoindex.functions.SplitRecursively`, `cocoindex.functions.CustomLanguageSpec`) -- Verified via `help()` in local venv

**Tree-sitter Grammars (Verified - HIGH confidence):**
- [tree-sitter-grammars/tree-sitter-hcl](https://github.com/tree-sitter-grammars/tree-sitter-hcl) -- HCL grammar exists but is NOT bundled in CocoIndex
- [camdencheek/tree-sitter-dockerfile](https://github.com/camdencheek/tree-sitter-dockerfile) -- Dockerfile grammar exists but is NOT bundled in CocoIndex
- [tree-sitter/tree-sitter-bash](https://github.com/tree-sitter/tree-sitter-bash) -- Bash grammar IS bundled in CocoIndex (built-in language)
- [Tree-sitter parser list](https://github.com/tree-sitter/tree-sitter/wiki/List-of-parsers) -- Comprehensive grammar catalog

**Terraform / HCL (Verified - HIGH confidence):**
- [Terraform Syntax Configuration](https://developer.hashicorp.com/terraform/language/syntax/configuration) -- HCL block types, label patterns
- [Terraform Block Reference](https://developer.hashicorp.com/terraform/language/block/terraform) -- terraform block structure
- [Terraform Import Block](https://developer.hashicorp.com/terraform/language/import) -- import block documentation
- [HCL Block Types Overview](https://spacelift.io/blog/hcl-hashicorp-configuration-language) -- Community guide to all block types

**Dockerfile (Verified - HIGH confidence):**
- [Dockerfile Reference](https://docs.docker.com/reference/dockerfile/) -- All 19 instruction types
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/) -- FROM...AS syntax, stage naming
- [BuildKit Parser (Go)](https://pkg.go.dev/github.com/moby/buildkit/frontend/dockerfile/parser) -- Official Dockerfile AST structure

**Bash (Verified - HIGH confidence):**
- [tree-sitter-bash grammar](https://github.com/tree-sitter/tree-sitter-bash) -- AST node types (function_definition, compound_statement, etc.)
- [ShellCheck](https://www.shellcheck.net/) -- Shell script static analysis (context for what analysis IS in scope for existing tools)

**Code Search Landscape (MEDIUM confidence):**
- [Sourcegraph Code Search](https://sourcegraph.com/docs/code-search/features) -- Feature comparison
- [Qdrant Code Search Tutorial](https://qdrant.tech/documentation/advanced-tutorials/code-search/) -- Semantic code search patterns
- [Pinecone Chunking Strategies](https://www.pinecone.io/learn/chunking-strategies/) -- General chunking best practices

---
*Feature research for: CocoSearch v1.2 DevOps Language Support*
*Researched: 2026-01-27*
