# Phase 2: Metadata Extraction - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Every DevOps chunk carries structured metadata identifying what it is — block type, hierarchy, and language. This phase creates a standalone metadata extraction module (`metadata.py`) that parses chunk text using regex to produce a `DevOpsMetadata` dataclass. Flow integration and schema changes are Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Extraction boundaries
- Claude's Discretion: Whether to match only at chunk-start or scan deeper — pick based on Phase 1 splitter output
- Claude's Discretion: How to handle chunks with multiple blocks — pick based on practical splitter behavior
- Claude's Discretion: Whether language_id is passed as input or auto-detected — pick cleanest architecture
- Separate extraction functions per language: `extract_hcl_metadata`, `extract_dockerfile_metadata`, `extract_bash_metadata` (not a single dispatcher)

### Hierarchy format
- Dot-separated hierarchy for HCL: `resource.aws_s3_bucket.data`, `data.aws_iam_policy.admin`, `module.vpc`
- Claude's Discretion: Variable depth for HCL blocks with fewer parts (e.g., `terraform` vs `resource.type.name`) — pick what's most useful for search/display
- Dockerfile non-FROM instructions inherit their stage context: e.g., RUN in builder stage gets `stage:builder`
- Dockerfile FROM without AS clause uses the image name as hierarchy (e.g., `image:ubuntu:22.04`)
- Bash uses `function:name` format for function chunks
- Claude's Discretion: Whether top-level Bash code gets empty hierarchy or a marker value

### Comment and string handling
- Explicitly skip comment lines before matching block keywords (not just position-based)
- Per-language comment syntax: HCL (#, //, /* */), Dockerfile (#), Bash (#)
- Claude's Discretion: Heredoc handling in HCL — assess risk based on Phase 1 splitting behavior
- Claude's Discretion: Dockerfile multi-line instruction parsing — pick based on complexity vs. practical risk

### Edge case defaults
- Unrecognized DevOps chunks get empty strings for block_type and hierarchy (same convention as non-DevOps files)
- language_id is ALWAYS populated for known DevOps files, even when block_type/hierarchy are empty (e.g., comment-only .tf chunk still gets language_id="hcl")
- DevOpsMetadata dataclass includes light validation (language_id must be one of: "hcl", "dockerfile", "bash", "")

### Claude's Discretion
- Whether to match at chunk-start only or scan deeper
- Single-block vs multi-block chunk handling strategy
- Language_id as input parameter vs auto-detection
- HCL variable-depth hierarchy formatting
- Top-level Bash code hierarchy value
- HCL heredoc guard necessity
- Dockerfile multi-line instruction parsing depth

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The roadmap success criteria provide concrete test cases:
- `resource "aws_s3_bucket" "data"` → block_type=resource, hierarchy=resource.aws_s3_bucket.data, language_id=hcl
- `FROM golang:1.21 AS builder` → block_type=FROM, hierarchy=stage:builder, language_id=dockerfile
- `deploy_app() {` → block_type=function, hierarchy=function:deploy_app, language_id=bash
- Python file chunk → block_type="", hierarchy="", language_id=""

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-metadata-extraction*
*Context gathered: 2026-01-27*
