# Domain Pitfalls

**Domain:** DevOps Language Support (HCL, Dockerfile, Bash) for Code Search
**Researched:** 2026-01-27
**Milestone:** v1.2 -- DevOps Language Support
**Confidence:** MEDIUM-HIGH

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or fundamental architecture failures.

### Pitfall 1: Regex Chunking Cannot Handle Nested Blocks in HCL

**What goes wrong:**
Regex-based separators in CocoIndex's `custom_languages` split HCL files at pattern boundaries, but HCL's deeply nested block structure (resource > provisioner > inline blocks, module > nested module calls) means regex patterns like `r"\nresource\s+"` split at the *start* of a block without understanding where it *ends*. Result: chunks contain the header of one resource and the body of the previous one. Worse, nested blocks like `dynamic` blocks inside resources get split mid-structure, producing chunks that are semantically meaningless.

**Why it happens:**
- Regex is fundamentally limited to regular languages; HCL's nested braces require a context-free grammar
- CocoIndex's `custom_languages` parameter accepts `separators_regex` -- a flat list of regex patterns for split boundaries, ordered by priority (higher-level first, lower-level later)
- These separators define *where to split*, not *what constitutes a complete block*
- HCL blocks can nest arbitrarily: `resource` > `provisioner` > `connection` > `inline` blocks
- A separator like `r"\nresource\s+"` matches the boundary but has no concept of the matching closing brace

**Consequences:**
- Search returns half-complete resource blocks (header of one, body of another)
- Metadata extraction produces incorrect resource types (associates wrong body with wrong header)
- Users searching for "aws_s3_bucket" get chunks containing the bucket header fused with the previous resource's body
- Full re-index required after fixing patterns

**Warning signs:**
- Chunks starting mid-block (e.g., starting with `}` or an attribute without a parent block)
- Metadata extraction yields resource types that don't match the chunk content
- Test HCL files with 3+ nested levels produce garbled chunks

**Prevention:**
1. Design separators to split at *top-level block boundaries only*: use `r"\n(?:resource|data|module|variable|output|locals|provider|terraform)\s+"` as the highest-priority separator
2. Accept that inner structure will be within a single chunk, not further split by nested block type
3. Set `chunk_size` large enough (2000-3000 bytes) that typical Terraform resources fit in a single chunk
4. Validate chunks with a simple brace-counting check: every chunk should have balanced `{` and `}` counts (or be explicitly the start/end of a block)
5. Use `chunk_overlap` (300-500 bytes) to ensure block boundaries are captured in adjacent chunks
6. Write integration tests with real-world Terraform files containing nested `dynamic` blocks, heredocs, and multi-level modules

**Detection strategy (automated):**
```python
def validate_chunk_braces(chunk_text: str) -> bool:
    """Check if braces are roughly balanced -- warns of mid-block splits."""
    return chunk_text.count("{") == chunk_text.count("}")
```

**Phase to address:** Phase 1 (Custom chunking patterns) -- this is foundational. Get wrong patterns here and everything downstream fails.

---

### Pitfall 2: HCL Heredoc Strings Break Regex Separator Matching

**What goes wrong:**
Terraform uses heredoc syntax (`<<EOF ... EOF` and `<<-EOF ... EOF`) for multi-line strings, inline policies, and embedded scripts. Regex separators that split on patterns like `r"\n\n"` or `r"\nresource\s+"` will match *inside* heredoc strings, splitting chunks in the middle of a JSON IAM policy or an embedded shell script. The word "resource" appearing inside an inline JSON policy would trigger a false split.

**Why it happens:**
- HCL heredoc strings can contain any text, including patterns that look like HCL block headers
- Example: an inline IAM policy heredoc containing `"Resource": "*"` matches a resource-looking pattern
- Regex has no concept of "I'm currently inside a heredoc" -- it operates on flat text
- `<<-EOF` (indented heredoc) strips leading whitespace, further confusing line-start patterns
- CocoIndex's `separators_regex` processes patterns against the entire text without context awareness

**Consequences:**
- Chunks split mid-heredoc, producing invalid JSON fragments in search results
- Metadata extraction tags a chunk as "resource" when it's actually inside a heredoc string
- Users searching for IAM policies get fragmented, unusable results
- Very common in real Terraform codebases (heredocs are used extensively for policies, scripts, templates)

**Warning signs:**
- Chunks containing `<<EOF` without matching `EOF` closer (or vice versa)
- JSON fragments appearing as standalone chunks
- Resource type metadata that doesn't correspond to actual HCL blocks

**Prevention:**
1. Avoid overly aggressive separator patterns -- prefer `r"\n(?:resource|data|module|variable|output|locals|provider|terraform)\s+"` which requires *line-start* block keywords (heredoc content is typically indented)
2. Set `chunk_size` generously (2000+ bytes) so heredoc-containing blocks stay in a single chunk
3. Accept some imperfect splits as a tradeoff -- regex chunking is *approximate*, not exact
4. In metadata extraction (post-chunking), validate extracted resource types by checking they appear at the start of the chunk or after a closing brace, not mid-string
5. For extremely large heredoc blocks (>2000 bytes), accept that the chunker will split them and add metadata noting "contains heredoc" for downstream filtering
6. Test with real-world Terraform files that use heredocs for IAM policies, user-data scripts, and template files

**Phase to address:** Phase 1 (Custom chunking patterns) -- pattern design must account for heredocs from the start.

---

### Pitfall 3: Metadata Extraction Produces False Positives from Chunk Content

**What goes wrong:**
Post-chunking metadata extraction uses regex to identify resource types, block types, and hierarchy from chunk text. But chunks may contain comments mentioning resource names, string literals containing block keywords, or variable names that look like resource references. The regex extracts metadata that doesn't reflect actual infrastructure, poisoning search results with incorrect type labels.

**Why it happens:**
- HCL: Comment `# This resource was replaced by aws_lambda_function` matches "resource" + "aws_lambda_function"
- Dockerfile: Comment `# FROM was changed to use alpine` matches "FROM"
- Bash: String `echo "function deploy completed"` matches a function pattern
- Metadata regex operates on chunk text without distinguishing code from comments/strings
- No AST available to distinguish structural elements from text content

**Consequences:**
- Search for "aws_lambda_function" returns chunks from comments about deprecated resources
- Search for Dockerfile "FROM" stages returns chunks from echo statements
- Metadata filters become unreliable, undermining the value proposition of rich metadata
- Users lose trust in metadata-filtered search results

**Warning signs:**
- Metadata resource_type counts don't match actual resource counts in the codebase
- Same resource type appearing in chunks from unrelated files
- Metadata extraction tests passing on simple examples but failing on real codebases

**Prevention:**
1. Design extraction regex to require structural context, not just keyword presence:
   - HCL: Require `^resource\s+"([^"]+)"\s+"([^"]+)"` at line start (not mid-line)
   - Dockerfile: Require `^FROM\s+` at line start (not after other text)
   - Bash: Require `^function\s+\w+` or `^\w+\s*\(\)` at line start
2. Strip comments before metadata extraction (simple for `#` comments, complex for inline `//`)
3. Assign confidence levels to extracted metadata: HIGH if at chunk start, LOW if mid-chunk
4. Store multiple candidate metadata entries per chunk rather than a single definitive label
5. Write tests with adversarial inputs: comments containing keywords, strings containing block syntax
6. Consider a lightweight pre-processing step that marks comment regions before regex extraction

**Phase to address:** Phase 2 (Metadata extraction) -- this cannot be fully solved in pattern design; requires extraction logic.

---

### Pitfall 4: Schema Migration Breaks Existing Indexes

**What goes wrong:**
v1.2 adds metadata columns (resource_type, block_type, hierarchy) to the collector export. CocoIndex's `flow.setup()` attempts an automatic schema migration (ALTER TABLE ADD COLUMN) on existing tables. If the migration changes primary keys or the new field structure is incompatible, CocoIndex drops and recreates the table, destroying all existing indexed data. Users must re-index their entire codebase.

**Why it happens:**
- CocoIndex uses automatic schema inference: the table schema is derived from the flow definition
- Adding new fields to `code_embeddings.collect(...)` changes the inferred schema
- CocoIndex's setup process "will try to do a non-destructive update if possible, e.g., primary keys don't change and target storage supports in-place schema update"
- If primary keys change (e.g., adding metadata fields to the primary key), CocoIndex drops and recreates
- Current primary key is `["filename", "location"]` -- changing this is destructive
- The `cocoindex_internal` state tables may also get out of sync with the target

**Consequences:**
- Full re-index required for all existing indexes (potentially hours of work)
- No warning before destructive migration
- Mixed indexes (some with metadata, some without) if migration partially fails
- Users upgrading from v1.1 lose all their indexed data

**Warning signs:**
- `flow.setup()` output mentions "drop" or "recreate" instead of "alter"
- Existing table row count drops to zero after setup
- Internal CocoIndex state becomes inconsistent (partial state for dropped tables)

**Prevention:**
1. Keep primary keys unchanged: `["filename", "location"]` -- never add metadata fields to primary key
2. Add metadata as nullable columns: `resource_type: str | None`, `block_type: str | None`, `hierarchy: str | None`
3. Test the migration path explicitly: create a v1.1-schema table, run v1.2 setup, verify data preserved
4. Document the upgrade path in release notes
5. Implement a `--dry-run` flag for setup to show what changes would be made
6. Consider using CocoIndex's `setup_by_user` option for the target if more control is needed
7. For v1.2 release: ensure metadata fields are purely additive (new columns with NULL defaults)

**Detection strategy:**
```bash
# Before upgrade: record row count
psql -c "SELECT count(*) FROM codeindex_myproject__myproject_chunks;"
# Run setup
# After: verify row count unchanged
psql -c "SELECT count(*) FROM codeindex_myproject__myproject_chunks;"
```

**Phase to address:** Phase 1 (Schema design) -- schema decisions constrain everything. Non-destructive migration must be verified before any implementation.

---

### Pitfall 5: Bash Chunking Fails on Heredocs and Nested Quoting

**What goes wrong:**
Bash scripts use heredocs (`<<EOF ... EOF`, `<<'EOF' ... EOF`, `<<-EOF ... EOF`) extensively for multi-line strings, embedded configs, and inline scripts for other languages. Regex separators split inside heredocs, producing chunks of embedded Python/JSON/YAML that have no Bash context. Additionally, nested quoting (`"$(command 'arg "inner"')"`) confuses any regex attempting to identify function or block boundaries.

**Why it happens:**
- Bash heredoc delimiters are arbitrary strings (`<<MYDELIM ... MYDELIM`), making regex detection impractical
- Quoted heredoc delimiters (`<<'EOF'`) suppress variable expansion but look different from unquoted ones
- Indented heredocs (`<<-EOF`) allow tabs before the delimiter
- Bash supports `$()` command substitution with independent quoting context, creating deeply nested quote structures
- Functions can be defined as `function_name() { ... }` or `function function_name { ... }` or `function function_name() { ... }` -- three syntaxes
- Function names in non-POSIX mode can contain unusual characters (`-`, `.`, `/`)

**Consequences:**
- Chunks contain fragments of embedded scripts (e.g., half a Python script inside a heredoc)
- Function detection regex misses functions using the `function` keyword without parentheses
- Search for "deploy function" returns heredoc fragments instead of actual Bash functions
- Metadata claims a chunk is a function when it's actually inside a case statement

**Warning signs:**
- Chunks starting with `EOF` or other heredoc terminators
- Function count in metadata doesn't match `grep -c "function\|().*{" script.sh`
- Chunks containing non-Bash syntax (Python, YAML, JSON embedded via heredoc)

**Prevention:**
1. Use conservative separators: split on `r"\n\n+"` (blank lines) and `r"\nfunction\s+\w+"` / `r"\n\w+\s*\(\)\s*\{"` only
2. Set large chunk sizes (2000+ bytes) for shell scripts -- most functions are 20-50 lines
3. Accept that Bash chunking will be less precise than Tree-sitter-supported languages
4. In metadata extraction, validate function detection by checking for balanced braces after the function signature
5. Document the limitation clearly: "Shell script chunking is approximate; complex scripts with large heredocs may produce imperfect chunks"
6. Test with real-world deployment scripts, CI/CD pipelines, and infrastructure automation scripts

**Phase to address:** Phase 1 (Custom chunking patterns) -- pattern design for Bash must be intentionally conservative.

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or degraded search quality.

### Pitfall 6: Dockerfile Chunking Ignores Multi-Stage Build Boundaries

**What goes wrong:**
Dockerfiles use `FROM` to start build stages. A regex separator like `r"\nFROM\s+"` correctly splits at stage boundaries, but doesn't capture the stage name (`AS builder`) as metadata. Without stage awareness, a chunk containing a `COPY --from=builder` instruction loses its cross-stage reference context. Search results show isolated instructions without build stage hierarchy.

**Why it happens:**
- Dockerfile multi-stage builds use `FROM image AS stage_name` syntax
- `COPY --from=stage_name` references previous stages but doesn't include the stage definition
- `ARG` before `FROM` applies globally but `ARG` after `FROM` is stage-scoped
- `ONBUILD` instructions trigger in downstream images, adding deferred execution context
- The `# syntax=docker/dockerfile:...` directive at file start affects parser behavior

**Consequences:**
- Search for "build stage" returns chunks without stage name context
- Metadata hierarchy shows flat structure instead of stage-based hierarchy
- Users cannot filter search results by build stage
- Cross-stage references (`COPY --from=`) appear without context about what they copy from

**Warning signs:**
- Dockerfile metadata missing stage names
- Search results showing COPY instructions without context about the source stage
- Multi-stage Dockerfiles being treated as flat sequences of instructions

**Prevention:**
1. Use `r"\nFROM\s+"` as the primary separator for Dockerfiles
2. In metadata extraction, parse the FROM line to extract: base image, stage name (if `AS` present), and stage index
3. Include stage context in hierarchy metadata: `"stage: builder (golang:1.21)"` or `"stage: 0 (ubuntu:22.04)"`
4. For `COPY --from=`, attempt to resolve the stage reference and include it in metadata
5. Test with multi-stage builds using named stages, numbered stages, and `ARG`-parameterized base images
6. Consider storing stage index as a metadata field for stage-based filtering

**Phase to address:** Phase 2 (Metadata extraction) -- separator patterns are straightforward; metadata extraction needs stage awareness.

---

### Pitfall 7: Chunk Size Too Small for DevOps Files

**What goes wrong:**
Current default `chunk_size=1000` bytes (set in `IndexingConfig`) works for programming languages where functions are typically 20-50 lines. DevOps files have different structural units: a Terraform resource is often 50-200 lines, a Dockerfile stage can be 30-100 lines, and Bash functions can include large heredocs. At 1000 bytes, most DevOps structural units get split across multiple chunks, destroying the semantic coherence that makes search useful.

**Why it happens:**
- Terraform resources include multiple nested blocks, attributes, and sometimes heredoc strings
- A typical AWS resource (e.g., `aws_ecs_task_definition`) can easily be 100+ lines / 3000+ bytes
- Dockerfile stages include RUN commands with long package install lists
- Bash functions embedding configuration via heredocs can be very large
- The 1000-byte default was optimized for Python/JS functions, not infrastructure code

**Consequences:**
- Terraform resources split across 2-3 chunks, losing structural coherence
- Search for "ECS task definition" returns 3 partial chunks instead of one complete resource
- Metadata extraction on partial chunks produces incomplete or incorrect resource types
- Embedding quality degrades (partial blocks produce poor semantic embeddings)

**Warning signs:**
- Average chunk count per file is much higher for `.tf` files than `.py` files
- Search results frequently return adjacent chunks from the same resource
- Resource type metadata found in first chunk but not subsequent chunks of same resource

**Prevention:**
1. Use language-specific chunk sizes: 2000-3000 bytes for HCL, 1500-2000 for Dockerfile, 2000 for Bash
2. Implement per-language `chunk_size` in `IndexingConfig` or in the custom language spec
3. Increase `chunk_overlap` proportionally (500+ bytes) to ensure block boundaries are in adjacent chunks
4. The `min_chunk_size` parameter (defaults to `chunk_size / 2`) prevents tiny fragments -- verify this works for DevOps files
5. Benchmark: index a real Terraform repo with different chunk sizes, measure chunk completeness
6. Consider a two-pass approach: first pass identifies structural units, second pass applies size limits only to oversized units

**Phase to address:** Phase 1 (Custom chunking patterns) -- chunk size configuration is part of initial pattern design.

---

### Pitfall 8: Metadata Extraction Adds Significant Indexing Latency

**What goes wrong:**
Adding regex-based metadata extraction for every chunk introduces per-chunk processing overhead. With 10+ regex patterns per language (resource types, block types, hierarchy parsing, function names), extraction adds 1-5ms per chunk. For a large infrastructure repo with 10,000+ chunks, this adds 10-50 seconds to indexing time. Combined with Ollama embedding latency, total indexing time becomes painfully slow.

**Why it happens:**
- Each chunk requires multiple regex matches for different metadata fields
- Regex compilation should happen once but is sometimes repeated per-chunk in naive implementations
- Complex regex patterns (especially with backtracking) can be slow on large chunks
- Metadata extraction runs sequentially between chunking and embedding in the CocoIndex flow
- No caching or batching for metadata operations

**Consequences:**
- Indexing time increases 20-50% for metadata-rich languages
- User perception: "v1.2 is much slower than v1.1"
- Incremental re-indexing of changed files still pays the full extraction cost

**Warning signs:**
- Profiling shows metadata extraction as a significant portion of per-file processing time
- Indexing time regression after v1.2 upgrade
- Large `.tf` files taking disproportionately longer than small ones

**Prevention:**
1. Pre-compile all regex patterns at module load time, not per-chunk
2. Use a single-pass extraction function that applies all patterns in one iteration over the text
3. Keep extraction logic lightweight: simple line-start patterns, no backtracking-heavy regex
4. Profile metadata extraction separately: measure ms/chunk with and without extraction
5. Consider making metadata extraction optional (configurable per index)
6. If extraction is slow, consider running it as a post-processing step rather than inline in the flow

**Phase to address:** Phase 2 (Metadata extraction implementation) -- design extraction for performance from the start.

---

### Pitfall 9: Metadata Column Filtering Interacts Poorly with pgvector Post-Filter

**What goes wrong:**
Adding metadata columns (resource_type, block_type, language_type) enables filtered search like "find all aws_s3_bucket resources." But pgvector applies WHERE clauses as post-filters after the vector similarity search. With HNSW index default `ef_search=40`, only ~40 candidates are evaluated. If only 5% are aws_s3_bucket, the query returns ~2 results instead of the requested 10, with no guarantee they're the best matches.

**Why it happens:**
- pgvector HNSW indexes don't natively support pre-filtering (before v0.8.0)
- pgvector 0.8.0+ added iterative index scans, but CocoSearch uses direct SQL queries against CocoIndex-managed tables
- Post-filtering discards candidates that don't match the WHERE clause
- With highly selective filters (specific resource types), most candidates are discarded
- The current CocoSearch query pattern already has this issue with language filters, and metadata filters compound it

**Consequences:**
- Filtered searches return fewer results than requested
- Users get incomplete search results when filtering by resource type
- Performance degrades as filter selectivity increases
- Users may conclude the tool doesn't work for infrastructure code

**Warning signs:**
- Filtered queries returning significantly fewer results than `limit`
- Query `EXPLAIN ANALYZE` showing index scan followed by filter removing 90%+ of rows
- Users reporting "search for aws_lambda_function returns only 1 result even though I have 20"

**Prevention:**
1. Increase `hnsw.ef_search` when metadata filters are present: `SET LOCAL hnsw.ef_search = 200;`
2. For pgvector 0.8.0+: enable iterative index scans with `SET hnsw.iterative_scan = relaxed_order;`
3. Over-fetch and post-filter in application code: request `limit * 5` from DB, filter in Python, return top `limit`
4. Consider partial indexes for common metadata values: `CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops) WHERE resource_type = 'aws_s3_bucket';`
5. Document that metadata filtering works best for broad categories (block_type = "resource") not narrow ones (resource_type = "aws_specific_thing")
6. Verify with `EXPLAIN ANALYZE` that filtered queries use the HNSW index and return adequate results

**Phase to address:** Phase 3 (Search integration) -- metadata filtering requires query-level tuning.

---

### Pitfall 10: Custom Language Patterns Conflict with Built-in Language Detection

**What goes wrong:**
CocoIndex's `SplitRecursively` matches the `language` parameter against custom languages first, then built-in languages. If a custom language name or alias conflicts with a built-in language name, unexpected behavior occurs. Conversely, if extensions like `.sh` happen to match a built-in language name that produces plain-text fallback, custom separators are bypassed entirely.

**Why it happens:**
- CocoIndex documentation states: "It's an error if any language name or alias is duplicated"
- The built-in language list includes 29+ languages with many file extensions
- The `language` parameter in CocoSearch's flow is set to `file["extension"]`, which yields the raw extension (e.g., "sh", "tf")
- If "sh" is not in the built-in list AND not registered as a custom language alias, it falls back to plain text
- If "sh" IS somehow in the built-in list (future CocoIndex version), it would conflict with a custom "sh" alias
- Currently confirmed NOT in built-in list: HCL, Terraform, Dockerfile, Bash, Shell

**Consequences:**
- DevOps files silently chunked as plain text instead of using custom separators
- Duplicate language name error at flow definition time (if names conflict)
- Subtle: files chunked correctly on one version, broken on next CocoIndex upgrade that adds built-in support

**Warning signs:**
- DevOps file chunks look like plain text splits (at blank lines/punctuation) not structural splits
- No error messages, just subtly worse chunk quality
- CocoIndex upgrade changes chunking behavior for previously-working files

**Prevention:**
1. Use explicit, unambiguous custom language names: "hcl_terraform", "dockerfile_custom", "bash_shell"
2. Register file extension aliases that match actual file extensions: `aliases=["tf", "hcl", "tfvars"]`
3. Test that custom separators are actually used: verify a known pattern produces the expected chunks
4. Pin CocoIndex version and test upgrades explicitly
5. Add a validation step that logs which language/chunking strategy was selected for each file
6. Write unit tests that verify custom language matching for each target extension

**Phase to address:** Phase 1 (Custom chunking configuration) -- language registration must be correct from the start.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without major rework.

### Pitfall 11: Inconsistent File Pattern Registration

**What goes wrong:**
DevOps files have inconsistent naming: `Dockerfile` (no extension), `Dockerfile.dev`, `docker-compose.yml`, `*.tf`, `*.tfvars`, `*.hcl`, `*.sh`, `*.bash`, `.bashrc`, `.bash_profile`. Missing any variant means those files are silently excluded from indexing. Users with `Dockerfile.prod` won't find their production Dockerfile in search.

**Prevention:**
1. Register comprehensive include patterns:
   - HCL: `["*.tf", "*.tfvars", "*.hcl", "*.tf.json"]`
   - Dockerfile: `["Dockerfile", "Dockerfile.*", "*.dockerfile", "docker-compose.yml", "docker-compose.*.yml", "compose.yml", "compose.*.yml"]`
   - Bash: `["*.sh", "*.bash", "*.zsh", ".bashrc", ".bash_profile", ".bash_aliases", ".profile", ".zshrc"]`
2. Test with repos that use non-standard naming conventions
3. Document which file patterns are supported in the CLI help

**Phase to address:** Phase 1 (File patterns) -- straightforward but easy to miss variants.

---

### Pitfall 12: Hierarchy Metadata Becomes Stale After Terraform Refactoring

**What goes wrong:**
Metadata stores hierarchy like `"module.vpc > resource.aws_subnet.public"`. When a user refactors Terraform (moves resources between modules, renames resources), the indexed hierarchy metadata becomes stale. Search results show old hierarchy paths that no longer exist. This is confusing but not critical since CocoSearch already handles this for file paths via incremental re-indexing.

**Prevention:**
1. Hierarchy metadata is recalculated on re-index (CocoIndex incremental processing handles this)
2. Hierarchy is best-effort: extracted from the chunk's content, not from cross-file module resolution
3. Document that hierarchy reflects the indexed state, not necessarily the current state
4. The same limitation exists for all metadata -- it's accurate only after re-indexing

**Phase to address:** Already handled by existing incremental indexing design. No special action needed.

---

### Pitfall 13: Language Detection Fails for Extensionless DevOps Files

**What goes wrong:**
`Dockerfile` has no file extension. The current `extract_extension` function returns empty string for extensionless files. Without an extension, the custom language matching falls through to plain-text chunking. The Dockerfile never gets its custom separators applied.

**Prevention:**
1. Enhance `extract_extension` or add a filename-to-language mapping function:
   ```python
   FILENAME_LANGUAGES = {
       "Dockerfile": "dockerfile",
       "Makefile": "makefile",
       "Vagrantfile": "ruby",
       "Jenkinsfile": "groovy",
   }
   ```
2. Check full filename first, then fall back to extension-based detection
3. Also handle `Dockerfile.dev`, `Dockerfile.prod` patterns (prefix matching)
4. Register "dockerfile" as a custom language with alias matching the detected name

**Phase to address:** Phase 1 (Language detection) -- needed before custom chunking can work for Dockerfiles.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Custom chunking patterns | Regex splits mid-block (Pitfall 1, 2, 5) | CRITICAL | Conservative separators, large chunk sizes, integration tests with real files |
| Custom chunking patterns | Chunk size too small (Pitfall 7) | MODERATE | Language-specific chunk sizes (2000+ bytes for DevOps) |
| Custom chunking patterns | Language detection fails (Pitfall 10, 13) | MODERATE | Explicit language names, filename-based detection, validation logging |
| File pattern registration | Missing file variants (Pitfall 11) | MINOR | Comprehensive glob patterns, documented coverage |
| Metadata extraction | False positives from comments/strings (Pitfall 3) | CRITICAL | Line-start patterns, confidence levels, comment stripping |
| Metadata extraction | Dockerfile stage context (Pitfall 6) | MODERATE | FROM-line parsing, stage name extraction |
| Metadata extraction | Performance overhead (Pitfall 8) | MODERATE | Pre-compiled regex, single-pass extraction, profiling |
| Schema migration | Destructive migration (Pitfall 4) | CRITICAL | Additive-only columns, stable primary keys, migration testing |
| Search integration | Post-filter returns too few results (Pitfall 9) | MODERATE | Increased ef_search, over-fetch strategy, iterative scans |

---

## Technical Debt Patterns (v1.2 Specific)

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single chunk_size for all languages | Simpler config | DevOps files chunked poorly | Never for v1.2 |
| Skip metadata extraction, chunk only | Faster delivery | No value over plain-text chunking | Only if timeline critical |
| Hardcode metadata regex in flow | Quick implementation | Hard to test, maintain, extend | MVP only; extract to module |
| Store metadata as JSON blob column | Flexible schema | Cannot index/filter individual fields | Never; use typed columns |
| Skip Dockerfile extensionless handling | Saves time | Dockerfiles never get custom chunking | Never |
| Skip heredoc test cases | Faster test writing | Regex bugs discovered in production | Never |

---

## Recovery Strategies (v1.2 Specific)

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Regex splits mid-block | MEDIUM | Fix separator patterns, re-index affected indexes |
| Metadata false positives | LOW | Fix extraction regex, re-index to regenerate metadata |
| Schema migration destroys data | HIGH | Re-index all codebases from scratch |
| Language detection miss | LOW | Fix detection, re-index affected files (incremental) |
| Chunk size too small | MEDIUM | Update config, re-index (CocoIndex incremental may require full re-process) |
| Post-filter returns too few | LOW | Adjust query parameters, no re-index needed |

---

## "Looks Done But Isn't" Checklist (v1.2)

- [ ] **HCL nested blocks:** Verify a Terraform file with 3+ nesting levels produces coherent chunks -- not just simple resource blocks
- [ ] **Heredoc handling:** Verify a Terraform file with IAM policy heredoc containing "resource" keyword doesn't split inside the heredoc
- [ ] **Dockerfile extensionless:** Verify `Dockerfile` (no extension) is detected and uses custom chunking, not plain text
- [ ] **Multi-stage Dockerfile:** Verify chunks align with stage boundaries and metadata includes stage names
- [ ] **Bash function variants:** Verify both `function_name() { }` and `function function_name { }` syntaxes are detected
- [ ] **Bash heredoc:** Verify a script with `<<EOF` heredoc containing a function definition doesn't extract the heredoc function as metadata
- [ ] **Schema migration:** Verify upgrading from v1.1 to v1.2 preserves existing index data (row count unchanged)
- [ ] **Metadata accuracy:** Spot-check 20 random chunks from a real Terraform repo -- metadata should match actual content >90% of the time
- [ ] **Search with metadata filter:** Verify `resource_type="aws_s3_bucket"` returns at least `limit/2` results when the codebase has that many
- [ ] **Performance regression:** Verify indexing time for a mixed codebase (Python + Terraform) is within 20% of v1.1

---

## Sources

- [CocoIndex Functions Documentation -- SplitRecursively, custom_languages, CustomLanguageSpec](https://cocoindex.io/docs/ops/functions) (HIGH confidence -- official docs, verified against installed v0.3.28 source)
- [CocoIndex Academic Papers Example -- custom_languages usage pattern](https://cocoindex.io/examples/academic_papers_index) (HIGH confidence -- official example)
- [CocoIndex Schema Inference Blog](https://cocoindex.io/blogs/handle-system-update-for-indexing-flow/) (HIGH confidence -- official blog on ALTER TABLE behavior)
- [Terraform HCL Syntax Reference](https://developer.hashicorp.com/terraform/language/syntax/configuration) (HIGH confidence -- official HashiCorp docs)
- [tree-sitter-grammars/tree-sitter-hcl](https://github.com/tree-sitter-grammars/tree-sitter-hcl) (MEDIUM confidence -- tree-sitter grammar exists but NOT used by CocoIndex's built-in SplitRecursively)
- [tree-sitter/tree-sitter-bash](https://github.com/tree-sitter/tree-sitter-bash) (MEDIUM confidence -- grammar exists but NOT used by CocoIndex)
- [camdencheek/tree-sitter-dockerfile](https://github.com/camdencheek/tree-sitter-dockerfile) (MEDIUM confidence -- grammar exists but NOT used by CocoIndex)
- [Docker Heredocs Blog](https://www.docker.com/blog/introduction-to-heredocs-in-dockerfiles/) (HIGH confidence -- official Docker blog)
- [BuildKit Dockerfile Parser Source](https://github.com/moby/buildkit/blob/master/frontend/dockerfile/parser/parser.go) (HIGH confidence -- reference parser implementation)
- [python-hcl2 Library](https://pypi.org/project/python-hcl2/) (MEDIUM confidence -- potential alternative for full HCL parsing)
- [pgvector 0.8.0 Iterative Index Scans](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/) (MEDIUM confidence -- AWS blog, applies to pgvector generally)
- [Bash Reference Manual -- Function Definition](https://www.gnu.org/software/bash/manual/bash.html) (HIGH confidence -- GNU official manual)
- [AST vs Regex Chunking for Code RAG](https://medium.com/@jouryjc0409/ast-enables-code-rag-models-to-overcome-traditional-chunking-limitations-b0bc1e61bdab) (MEDIUM confidence -- research overview)
- [Tenable terrascan -- HCL Nested Block Parsing Issues](https://github.com/tenable/terrascan/issues/233) (MEDIUM confidence -- real-world parsing failure case)
- [PlanetScale: Backward Compatible Database Changes](https://planetscale.com/blog/backward-compatible-databases-changes) (MEDIUM confidence -- general migration pattern)
- [Docker Multi-Stage Build ARG/ENV Scoping](https://github.com/moby/moby/issues/37345) (HIGH confidence -- official Docker issue documenting behavior)

---

*Pitfalls research for: CocoSearch v1.2 (DevOps Language Support)*
*Researched: 2026-01-27*
