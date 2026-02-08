# Phase 47: Documentation Update - Research

**Researched:** 2026-02-08
**Domain:** Documentation rewrite for infra-only Docker model, new defaults, and protocol enhancements
**Confidence:** HIGH

## Summary

This phase is a documentation-only effort updating 8 markdown files (README.md + 7 docs/) to accurately describe the current system state after phases 43-46. The primary changes are: (1) the Docker model shifted from all-in-one to infra-only (PostgreSQL+Ollama only, CocoSearch runs natively via uvx), (2) DATABASE_URL now has a default matching Docker credentials so env vars are optional, (3) MCP protocol enhancements added Roots-based project detection, and (4) parse failure tracking was added to stats output.

The CONTEXT.md decisions constrain this work tightly: rely on GitHub's sidebar ToC (no manual ToC), show commands only (no expected output blocks), use `uvx cocosearch` everywhere, assume Docker Desktop and uv/uvx are pre-installed, and describe current state only (no migration notes). The documentation should be friendly and conversational, pragmatic and task-oriented.

**Primary recommendation:** Perform a systematic audit-and-rewrite of each documentation file, starting with the README (highest visibility), then mcp-configuration.md, cli-reference.md, architecture.md, and the remaining reference docs. Each file gets the same treatment: verify section headers are clear for GitHub sidebar navigation, ensure all content reflects current state, use `uvx cocosearch` throughout, remove output blocks, and add cross-reference links where natural.

## Standard Stack

Not applicable -- this phase is documentation-only, no libraries or tools involved.

### Tools Used

| Tool | Purpose | Why |
|------|---------|-----|
| Markdown | Documentation format | GitHub-native rendering with auto-sidebar ToC |
| GitHub auto-ToC | Navigation | GitHub generates clickable ToC button from headings in any .md file with 2+ headings |

## Architecture Patterns

### Documentation File Inventory

Current files requiring updates, with scope assessment:

| File | Lines | Scope of Changes |
|------|-------|-----------------|
| `README.md` | 157 | **Major rewrite** -- restructure Getting Started, add docs section, streamline |
| `docs/mcp-configuration.md` | 226 | **Major rewrite** -- simplify around optional DATABASE_URL, update registration examples |
| `docs/cli-reference.md` | 217 | **Moderate** -- remove output blocks, use `uvx cocosearch`, add parse health CLI flags |
| `docs/architecture.md` | 89 | **Moderate** -- update Docker description, mention Roots detection, parse tracking |
| `docs/mcp-tools.md` | 355 | **Moderate** -- update index_stats with include_failures param, note async search_code |
| `docs/retrieval.md` | 370 | **Minor** -- mostly current, add parse tracking mention in indexing pipeline |
| `docs/search-features.md` | 123 | **Minor** -- mostly current, no significant changes needed |
| `docs/dogfooding.md` | 110 | **Moderate** -- remove output blocks, use `uvx cocosearch` |

### Documentation Structure Decisions (from CONTEXT.md -- locked)

1. **No manual ToC** -- GitHub auto-generates a clickable ToC button in the file header for any markdown file with 2+ headings. This works for docs hosted on GitHub.
2. **Clear section headers** -- Use descriptive `##` and `###` headers so the GitHub sidebar navigation works well.
3. **Flat docs/ folder** -- No subfolders, no docs/INDEX.md.
4. **README docs section** -- README includes links to each doc in docs/.
5. **Cross-references via inline links** -- No "See Also" sections; link naturally within text.
6. **Friendly, conversational tone** -- Like Vercel or Supabase docs.
7. **Current state only** -- No migration notes, no "changed in vX" callouts.
8. **Commands only, no output** -- Remove all "Expected output:" and output blocks.
9. **`uvx cocosearch` everywhere** -- This is the recommended invocation pattern.
10. **Assume Docker Desktop + uv/uvx pre-installed** -- No install instructions for these.

### README Target Structure

Based on CONTEXT.md decisions (3-step quick-start, MCP as primary use case, Docker as primary path):

```
# CocoSearch
  [tagline + what it does]

## Quick Start
  [3 steps: docker compose up -> index -> use via MCP]

## Features
  [bullet list]

## Supported Languages
  [brief summary + command]

## Components
  [PostgreSQL, Ollama, CocoSearch]

## Setup
### Docker (Recommended)
  [docker compose up -d]
### Manual Setup (Alternative)
  [brief manual PostgreSQL + Ollama instructions]

## Using CocoSearch
### MCP Registration (Recommended)
  [Claude Code single registration, mention Desktop]
### CLI
  [basic examples]

## Configuration
  [.cocosearch.yaml]

## Documentation
  [links to each doc in docs/]

## Skills
  [links to skills]
```

### MCP Configuration Doc Target Structure

```
## Configuring MCP
  [intro paragraph]

### Prerequisites
  [docker compose up -d, note DATABASE_URL optional]

### Single Registration (Recommended)
  [Claude Code with uvx]

### Claude Code
  [detailed setup]

### Claude Desktop
  [config file]

### OpenCode
  [config file]

### Per-Project Registration
  [alternative pattern]
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table of contents | Manual markdown ToC at top of each doc | GitHub's auto-generated sidebar ToC button | CONTEXT.md decision; auto-maintained; no staleness risk |
| Documentation index page | docs/INDEX.md | README docs section with links | CONTEXT.md decision; single entry point |

## Common Pitfalls

### Pitfall 1: Stale References to Old Docker Model

**What goes wrong:** Documentation refers to the all-in-one Docker image running CocoSearch inside the container, exposes port 3000, or describes `docker run` as starting the MCP server.
**Why it happens:** The Docker model changed in phases 43-44 from all-in-one to infra-only. Multiple docs were partially updated but may still have vestiges.
**How to avoid:** Audit every mention of Docker across all docs. Docker only provides PostgreSQL (port 5432) and Ollama (port 11434). CocoSearch always runs natively via `uvx cocosearch`.
**Warning signs:** Any mention of port 3000, "MCP server in Docker", Python in Docker image, or `docker run ... cocosearch mcp`.

### Pitfall 2: DATABASE_URL Shown as Required

**What goes wrong:** Documentation shows `COCOSEARCH_DATABASE_URL` as a required environment variable or shows it being explicitly set in MCP config examples.
**Why it happens:** Before phase 43, DATABASE_URL had no default and was mandatory.
**How to avoid:** DATABASE_URL defaults to `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch`. When using Docker (either compose or all-in-one image), no env vars need to be set. MCP registration commands should NOT include `--env COCOSEARCH_DATABASE_URL=...` in the recommended (Docker) path.
**Warning signs:** `--env COCOSEARCH_DATABASE_URL=...` in command examples without qualification, "Set this environment variable" instructions.

### Pitfall 3: Using `uv run` Instead of `uvx`

**What goes wrong:** Examples show `uv run cocosearch` or `uv run --directory /path cocosearch` instead of the recommended `uvx cocosearch`.
**Why it happens:** Earlier docs used `uv run` since the project was run from source. The `uvx` pattern is the intended user-facing invocation.
**How to avoid:** All examples must use `uvx cocosearch` or `uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch`.
**Warning signs:** Any `uv run cocosearch` in user-facing docs (dogfooding.md may be an exception since it demos dev workflow).

### Pitfall 4: Including Output Blocks

**What goes wrong:** Documentation includes "Expected output:" blocks showing terminal output.
**Why it happens:** The original docs (phase 7) included output blocks for clarity.
**How to avoid:** CONTEXT.md decision: show commands only, no expected output blocks. Remove all output blocks.
**Warning signs:** Fenced code blocks preceded by "Output:", "Expected output:", or indented output blocks after commands.

### Pitfall 5: Missing New Features in Reference Docs

**What goes wrong:** New features from phases 45-46 (Roots detection, parse health stats, `include_failures` parameter) are not documented.
**Why it happens:** These features were added after the original docs were written.
**How to avoid:** Cross-reference the feature inventory below against each doc file.
**Warning signs:** No mention of parse health in mcp-tools.md, no mention of `--show-failures` in cli-reference.md.

### Pitfall 6: Inconsistent Quick Start Flow

**What goes wrong:** README quick-start shows too many steps, or shows CLI before MCP, or shows manual setup before Docker.
**Why it happens:** README currently has 3 options (all-in-one Docker, compose, dev-setup).
**How to avoid:** CONTEXT.md decision: 3-step quick-start (docker compose up -> index -> use via MCP). Docker compose is the primary path. MCP registration leads, CLI is secondary.
**Warning signs:** More than 3 steps in quick-start, CLI examples before MCP registration.

## Code Examples

### Docker Compose Quick Start (verified from docker-compose.yml)

```bash
docker compose up -d
```

This starts PostgreSQL 17 with pgvector on port 5432 and Ollama with nomic-embed-text on port 11434. Credentials: cocosearch/cocosearch (matches the app default).

### Install and Run CocoSearch

```bash
uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch --help
```

### Index a Codebase

```bash
uvx cocosearch index /path/to/project
```

### MCP Registration (Claude Code, Single Registration)

```bash
claude mcp add --scope user cocosearch -- \
  uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch mcp --project-from-cwd
```

No `--env COCOSEARCH_DATABASE_URL=...` needed when using Docker compose (default credentials match).

### MCP Registration (Claude Desktop)

```json
{
  "mcpServers": {
    "cocosearch": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/VioletCranberry/coco-s",
        "cocosearch",
        "mcp",
        "--project-from-cwd"
      ]
    }
  }
}
```

### CLI Stats with Parse Health

```bash
uvx cocosearch stats myproject --pretty
uvx cocosearch stats myproject --pretty --show-failures
```

### MCP index_stats with include_failures

The `index_stats` MCP tool now accepts `include_failures` (boolean, default false):

```json
{
  "index_name": "my-project",
  "include_failures": true
}
```

## Feature Inventory: Changes from Phases 43-46

These features must be reflected in documentation. Checklist for the planner:

### Phase 43: Bug Fix & Credential Defaults
- [x] `COCOSEARCH_DATABASE_URL` has default: `postgresql://cocosearch:cocosearch@localhost:5432/cocosearch`
- [x] docker-compose.yml uses cocosearch:cocosearch credentials (already updated)
- [x] .env.example marks DATABASE_URL as optional (already updated)
- [x] `config check` shows "default" source when using default URL

### Phase 44: Docker Image Simplification
- [x] Docker image is infra-only (no Python, no MCP server)
- [x] Base image: debian:bookworm-slim (not python:3.11-slim)
- [x] PostgreSQL 17 (not 16)
- [x] Only ports 5432 and 11434 exposed (no 3000)
- [x] No svc-mcp service in s6-overlay
- [x] README and MCP docs partially updated in 44-02

### Phase 45: MCP Protocol Enhancements
- [ ] `search_code` is now async (accepts `ctx: Context`)
- [ ] MCP Roots capability for automatic project detection
- [ ] Project detection priority chain: roots > query_param > env > cwd
- [ ] HTTP transport `?project=` query parameter
- [ ] `file://` URI parsing for Roots
- [ ] Hint message for non-Roots clients

### Phase 46: Parse Failure Tracking
- [ ] Parse status detection (ok/partial/error/unsupported) for indexed files
- [ ] `index_stats` MCP tool has new `include_failures` parameter (boolean, default false)
- [ ] CLI `stats` command shows parse health by default
- [ ] CLI `stats --show-failures` flag for detailed failure listing
- [ ] HTTP `/api/stats?include_failures=true` parameter
- [ ] Parse results table created per index, cleaned up on `clear_index`

### Cross-cutting
- [ ] All code examples use `uvx cocosearch` (not `uv run`)
- [ ] No output blocks in any doc
- [ ] Clear section headers for GitHub sidebar ToC
- [ ] README has docs section linking to each doc
- [ ] Inline cross-references between docs

## Gap Analysis: Current Docs vs. Required State

### README.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Getting Started | 3 options (Docker build, compose, dev-setup) | 3-step quick-start (compose up, index, MCP) | **Major restructure** |
| MCP section | Detailed MCP registration with DATABASE_URL env | Simplified (no env needed with Docker) | **Simplify** |
| Docker model | Partially updated in 44-02 (infra-only) | Clean infra-only description | **Review and polish** |
| Docs section | Ad-hoc links scattered in text | Dedicated docs section with all links | **Add section** |
| Output blocks | Some present | None | **Remove** |
| Invocation | Mix of `uvx` patterns | Consistent `uvx cocosearch` | **Standardize** |
| Dogfooding link | Broken: `./docs/dogfooding.md.` (trailing period) | Fixed link | **Fix** |
| Search features link | Broken: `./docs/search-features.md.` (trailing period) | Fixed link | **Fix** |

### docs/mcp-configuration.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Prerequisites | Shows Docker + all-in-one options | Docker compose as primary | **Simplify** |
| DATABASE_URL | Shown in all examples, noted as optional | Not in recommended examples, note only for override | **Remove from examples** |
| Per-project section | Shows `uv run --directory` pattern | Show `uvx` pattern | **Update** |
| Roots detection | Not mentioned | Mention automatic project detection via Roots | **Add** |
| OpenCode config | Shows `uv run` | Show `uvx` | **Update** |

### docs/cli-reference.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Output blocks | Present throughout | Remove all | **Remove** |
| Invocation | `cocosearch` (bare) | `uvx cocosearch` or just `cocosearch` (both are fine, but be consistent) | **Review** |
| Parse health | Not mentioned | Document `--show-failures` flag and parse health output | **Add** |
| Stats command | Basic stats shown | Update to reflect comprehensive stats with parse health | **Update** |

### docs/architecture.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Docker description | Partially current | Describe infra-only model explicitly | **Update** |
| MCP integration | 5 tools listed, transport support | Add Roots capability mention | **Add** |
| Parse tracking | Not mentioned | Add brief mention in indexing pipeline or key decisions | **Add** |

### docs/mcp-tools.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| search_code | Sync signature shown | Note it is async with Context (implementation detail, may not matter for API docs) | **Minor** |
| index_stats | No include_failures param | Add include_failures parameter | **Add** |
| Parse health | Not in stats response | Add parse_stats and parse_health_pct to response examples | **Add** |

### docs/retrieval.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Indexing pipeline | 7 stages documented | Add parse tracking as post-indexing step | **Minor add** |
| Content | Thorough and accurate | Mostly current | **Minor** |

### docs/search-features.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Content | Accurate for search features | No significant changes needed | **Minimal** |
| Output blocks | Some output blocks present | Remove | **Remove** |

### docs/dogfooding.md

| Area | Current State | Required State | Gap |
|------|--------------|----------------|-----|
| Commands | Uses `uv run cocosearch` | Use `uvx cocosearch` | **Update** |
| Output blocks | Present throughout | Remove | **Remove** |

## Planning Guidance

### Recommended Plan Structure

Given the scope, 2 plans are appropriate:

**Plan 1: README + MCP Configuration (highest impact, most complex)**
- Full README restructure following the target structure above
- MCP configuration doc rewrite removing DATABASE_URL from examples
- These are the two highest-visibility docs and are tightly coupled (README links to MCP docs)

**Plan 2: Reference Docs Update (cli-reference, architecture, mcp-tools, retrieval, search-features, dogfooding)**
- Systematic pass through each reference doc
- Add parse health features to cli-reference and mcp-tools
- Remove output blocks from all docs
- Update invocation patterns to `uvx cocosearch`
- Add Roots mention to architecture.md
- Fix broken links

### Key Verification Points

For each doc file, verify:
1. No manual ToC at top (rely on GitHub sidebar)
2. Section headers are clear and descriptive (for GitHub sidebar navigation)
3. No output blocks remain
4. All commands use `uvx cocosearch`
5. No `COCOSEARCH_DATABASE_URL` in examples without qualification
6. No references to port 3000, Python in Docker, or all-in-one Docker running MCP
7. Cross-references to other docs where naturally relevant
8. Tone is friendly and conversational

## Open Questions

1. **Dogfooding.md scope:** The CONTEXT.md says "always use `uvx cocosearch`" but dogfooding.md specifically demonstrates the dev workflow. Should it use `uvx cocosearch` or keep `uv run cocosearch` since it is about developing CocoSearch itself? **Recommendation:** Use `uvx cocosearch` since the doc is about using CocoSearch to search its own code, not about developing CocoSearch. The dev workflow is separate.

2. **Skills section in README:** The current README has a skills section with links. The CONTEXT.md doesn't explicitly mention skills. **Recommendation:** Keep the skills section but move it to after the docs section. It is existing content that is still accurate.

3. **dev-setup.sh reference:** Currently README Option #3 mentions `dev-setup.sh`. The CONTEXT.md says Docker is primary and manual is alternative. **Recommendation:** Remove dev-setup.sh from the main README flow. It is a developer tool, not a user-facing setup path. Can be briefly mentioned or linked in a "Development" section if desired.

## Sources

### Primary (HIGH confidence)
- Direct reading of all 8 documentation files in the repository
- Direct reading of source code (server.py, cli.py, env_validation.py, docker-compose.yml, Dockerfile)
- Phase 43-46 SUMMARY.md files documenting all changes
- CONTEXT.md with locked decisions for this phase
- STATE.md with accumulated project decisions
- REQUIREMENTS.md with DOC-01 through DOC-04 specifications

### Secondary (MEDIUM confidence)
- [GitHub Table of Contents support in Markdown files](https://github.blog/changelog/2021-04-13-table-of-contents-support-in-markdown-files/) - Confirms GitHub auto-generates a ToC button for markdown files with 2+ headings

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Documentation inventory: HIGH - direct file reading
- Gap analysis: HIGH - compared current docs against source code and phase summaries
- Feature inventory: HIGH - verified against source code
- Architecture patterns: HIGH - derived from locked CONTEXT.md decisions
- Planning guidance: MEDIUM - based on scope assessment and phase structure patterns

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (documentation is stable domain; 30 days)
