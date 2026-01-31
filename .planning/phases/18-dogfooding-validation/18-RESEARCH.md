# Phase 18: Dogfooding Validation - Research

**Researched:** 2026-01-31
**Domain:** Self-referential documentation and configuration demonstration
**Confidence:** HIGH

## Summary

Phase 18 is a documentation and configuration phase that demonstrates CocoSearch's value by using it on itself. This is a well-established pattern called "dogfooding" in software development, where a tool demonstrates its capabilities through self-application.

The technical work is minimal - the configuration system (Phase 15), CLI (Phase 16), and dev-setup.sh script (Phase 17) are complete. This phase creates two artifacts:
1. A `cocosearch.yaml` config file showing minimal, effective configuration
2. A README section with 3-4 annotated example searches of the CocoSearch codebase

The context decisions are locked: index name "self", include Python/DevOps/Markdown files, include test directories, rely on default excludes, keep config minimal, place README section after Quick Start, use CLI commands only (not REPL), include verification step with `cocosearch stats self`.

**Primary recommendation:** Create minimal config demonstrating defaults work well, write brief README section with architecture/implementation query examples showing annotated output, verify with stats command.

## Standard Stack

### Core

No external libraries needed - this is pure documentation and YAML configuration.

| Component | Purpose | Why Standard |
|-----------|---------|--------------|
| YAML | Config file format | Already used by cocosearch.yaml schema (Phase 15) |
| Markdown | Documentation format | README.md standard for GitHub repositories |
| Bash | Verification commands | CLI already exists, just documenting usage |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| cocosearch CLI | Indexing and search | All example commands use existing CLI |
| dev-setup.sh | Full environment setup | Cross-reference for new contributors |

### Alternatives Considered

None - the stack is predetermined by existing implementation.

## Architecture Patterns

### Recommended File Structure

```
/
├── cocosearch.yaml          # New: Dogfooding config
└── README.md                # Modified: Add "Searching CocoSearch" section
```

### Pattern 1: Minimal Configuration File

**What:** Demonstrate that CocoSearch's defaults work well by showing a config that mostly relies on defaults

**When to use:** For the dogfooding config - shows new users they don't need extensive configuration

**Example:**
```yaml
# CocoSearch using CocoSearch
indexName: self

indexing:
  includePatterns:
    - "*.py"
    - "*.sh"
    - "*.bash"
    - "Dockerfile*"
    - "docker-compose*.yml"
    - "*.md"
  # Rely on defaults for excludePatterns - demonstrates .gitignore works
  # Rely on defaults for chunk settings - demonstrates sensible defaults
```

**Rationale:** The context decisions specify "keep config minimal - demonstrates defaults work well" and "rely on CocoSearch's default exclude patterns (no explicit __pycache__, .git, .venv)". This shows users they can trust the defaults.

### Pattern 2: Annotated Example Commands

**What:** Show CLI command followed by truncated/annotated output explaining what was found

**When to use:** In README dogfooding section - helps users understand what results look like

**Example structure:**
```markdown
### Search for authentication patterns

```bash
cocosearch search "how does embedding work" --index self --pretty
```

Finds the embedder module implementation:

```
[1] src/cocosearch/indexer/embedder.py:15-45 (score: 0.87)
    class OllamaEmbedder:
        """Generate embeddings using Ollama."""
        ...
```
```

**Rationale:** Based on ripgrep README analysis and context decision "include annotated output showing what was found". Helps users understand the tool's value before installing.

### Pattern 3: Standalone Commands

**What:** Example commands don't assume user ran dev-setup.sh or has environment pre-configured

**When to use:** All README examples - maximizes accessibility

**Example:**
```bash
# Works from any state - doesn't assume COCOINDEX_DATABASE_URL is set
uv run cocosearch search "query" --index self --pretty

# Not: cocosearch search "query" (assumes setup)
```

**Rationale:** Context decision "standalone commands - doesn't assume user ran dev-setup.sh". Makes examples copy-pasteable for users exploring the project.

### Anti-Patterns to Avoid

- **Extensive config**: Don't override all defaults - defeats the purpose of showing minimal config works
- **REPL examples**: Context specifies "CLI commands only (not REPL)" for simplicity
- **Long output dumps**: Context specifies "annotated output" not full output - show enough to understand value
- **Implementation-only queries**: Context specifies "mix of implementation and architecture questions" for balanced demonstration

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config validation | Manual YAML checks | Existing Pydantic schema | Schema in src/cocosearch/config/schema.py handles validation |
| File pattern defaults | Hardcoded list in YAML | Rely on IndexingConfig defaults | Phase 15 implemented comprehensive defaults in src/cocosearch/indexer/config.py |
| Example search queries | Made-up queries | Real queries about codebase | Dogfooding requires authentic usage, not contrived examples |

**Key insight:** The infrastructure is complete - this phase is about demonstration, not implementation. Use existing commands and config schema as-is.

## Common Pitfalls

### Pitfall 1: Over-configuration

**What goes wrong:** Config file includes many overrides and explicit settings, defeating the "minimal config" goal

**Why it happens:** Tendency to be thorough and explicit in configuration files

**How to avoid:** Only specify index name and include patterns (per context). Trust defaults for excludes, chunk settings, search settings

**Warning signs:** Config file has comments explaining every field, multiple sections with overrides

### Pitfall 2: Stale Example Output

**What goes wrong:** Annotated output examples show results that don't match actual search results

**Why it happens:** Codebase changes after examples are written, examples become outdated

**How to avoid:**
- Run actual searches while writing examples, copy real output
- Use truncated output (first 2-3 results) to reduce maintenance burden
- Include verification task: run example commands and confirm output is plausible

**Warning signs:** File paths in examples don't exist, score values seem unrealistic

### Pitfall 3: Missing Verification Step

**What goes wrong:** User can't confirm indexing worked

**Why it happens:** Focus on search examples, forget to show how to verify index exists

**How to avoid:** Context specifies "Include verification step: `cocosearch stats self` after indexing"

**Warning signs:** README shows indexing and searching but no way to check index status

### Pitfall 4: Wrong Command Name

**What goes wrong:** Examples use `cocosearch info self` instead of `cocosearch stats self`

**Why it happens:** Common CLI pattern is `info` subcommand, but CocoSearch uses `stats`

**How to avoid:** Verify CLI command exists before documenting: `uv run cocosearch stats --help`

**Warning signs:** Command not found errors when testing examples

### Pitfall 5: Forgetting Test Files in Config

**What goes wrong:** Config excludes tests/unit/ and tests/integration/ directories

**Why it happens:** Common pattern to exclude test files from production indexing

**How to avoid:** Context decision: "Include test files (tests/unit/, tests/integration/) - useful for finding test patterns"

**Warning signs:** Config has excludePatterns with test paths, or lacks includePatterns covering test files

## Code Examples

Verified patterns from existing codebase:

### Config File Format (camelCase fields)

Source: src/cocosearch/config/schema.py

```yaml
# CocoSearch config uses camelCase for consistency with Pydantic models
indexName: self

indexing:
  includePatterns:    # Not include_patterns
    - "*.py"
  excludePatterns: []  # Not exclude_patterns
  chunkSize: 1000      # Not chunk_size
  chunkOverlap: 300    # Not chunk_overlap
```

**Critical detail:** The schema uses camelCase (includePatterns, excludePatterns, chunkSize, chunkOverlap) NOT snake_case. This is defined in src/cocosearch/config/schema.py lines 17-21.

### Default Include Patterns (Source: src/cocosearch/indexer/config.py)

```python
include_patterns: list[str] = [
    "*.py",      # Python
    "*.sh",      # Bash
    "*.bash",    # Bash
    "Dockerfile",
    "Dockerfile.*",
    "*.md",      # Markdown
    # ... 60+ other patterns
]
```

For CocoSearch dogfooding, we need:
- Python: `*.py` (core implementation)
- Bash: `*.sh`, `*.bash` (dev-setup.sh)
- Docker: `Dockerfile*`, `docker-compose*.yml` (infrastructure)
- Markdown: `*.md` (documentation)

### CLI Commands for README Examples

Source: Verified with `uv run cocosearch --help`

```bash
# Index the codebase
uv run cocosearch index . --name self

# Verify indexing worked
uv run cocosearch stats self --pretty

# Search with natural language
uv run cocosearch search "how does indexing work" --index self --pretty

# Filter by language
uv run cocosearch search "docker setup" --index self --lang bash --pretty
```

Note: Command is `stats` not `info` (verified via CLI help output).

### README Section Placement

Source: README.md structure analysis

Current README structure:
1. Header and description
2. Architecture diagram
3. Table of Contents
4. Quick Start (lines 48-78)
5. Installation (lines 79-156)
6. MCP Configuration (lines 157-303)
7. CLI Reference (lines 305-442)
8. Configuration (lines 443-471)

**Insert new section after Quick Start (around line 79):**

```markdown
## Searching CocoSearch

CocoSearch uses CocoSearch to index its own codebase...

[Examples here]

**Need the full development environment?** See [dev-setup.sh](dev-setup.sh) for automated setup.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate example projects | Self-referential dogfooding | Established pattern (2020+) | Users see authentic usage, not contrived demos |
| Verbose config files | Minimal config demonstrating defaults | Modern UX trend (2022+) | Lower barrier to entry, shows tool works out-of-box |
| README as reference manual | README as quick start + real examples | GitHub standard (2023+) | Faster time-to-value for new users |

**Current best practices (2026):**
- Dogfooding is cultural and systematic, not ad-hoc (per [Userpilot](https://userpilot.com/blog/product-dogfooding/) and [TestDevLab](https://www.testdevlab.com/blog/dogfooding-a-quick-guide-to-internal-beta-testing))
- Self-referential examples in README show tool quality (per [awesome-readme](https://github.com/matiassingers/awesome-readme) - Hexworks/Zircon example)
- CLI tools show command + output snippets, not full dumps (per ripgrep README pattern)

## Open Questions

None - this is a straightforward documentation task with locked decisions.

## Sources

### Primary (HIGH confidence)

- **Existing codebase analysis:**
  - `/Users/fedorzhdanov/GIT/personal/coco-s/src/cocosearch/config/schema.py` - Config field names (camelCase)
  - `/Users/fedorzhdanov/GIT/personal/coco-s/src/cocosearch/indexer/config.py` - Default include patterns
  - `/Users/fedorzhdanov/GIT/personal/coco-s/src/cocosearch/config/generator.py` - Config template
  - `/Users/fedorzhdanov/GIT/personal/coco-s/README.md` - Current structure
  - `/Users/fedorzhdanov/GIT/personal/coco-s/dev-setup.sh` - Setup script reference
  - CLI verification: `uv run cocosearch --help` and `uv run cocosearch stats --help`

- **Context decisions:**
  - `/Users/fedorzhdanov/GIT/personal/coco-s/.planning/phases/18-dogfooding-validation/18-CONTEXT.md` - All implementation decisions locked

### Secondary (MEDIUM confidence)

- [Product Dogfooding in Software Development - Userpilot](https://userpilot.com/blog/product-dogfooding/) - Best practices for dogfooding
- [Dogfooding: A Quick Guide to Internal Beta Testing - TestDevLab](https://www.testdevlab.com/blog/dogfooding-a-quick-guide-to-internal-beta-testing) - Structured approach
- [awesome-readme - GitHub](https://github.com/matiassingers/awesome-readme) - Self-referential documentation examples
- [ripgrep README patterns - WebFetch analysis](https://github.com/BurntSushi/ripgrep) - Example command documentation style

### Tertiary (LOW confidence)

None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, using existing YAML/Markdown/CLI
- Architecture: HIGH - Patterns derived from existing codebase and context decisions
- Pitfalls: HIGH - Identified through codebase analysis (e.g., camelCase vs snake_case, stats vs info)

**Research date:** 2026-01-31
**Valid until:** 2026-04-30 (90 days - stable documentation patterns, unlikely to change)

**Key decisions locked by CONTEXT.md:**
- Index name: `self`
- File types: Python, DevOps (Dockerfile, docker-compose, bash), Markdown
- Include test files: tests/unit/, tests/integration/
- Config philosophy: Minimal, rely on defaults
- README section: After Quick Start, 3-4 examples, CLI only
- Verification: `cocosearch stats self` command
