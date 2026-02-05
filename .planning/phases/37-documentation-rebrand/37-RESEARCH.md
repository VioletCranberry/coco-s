# Phase 37: Documentation Rebrand - Research

**Researched:** 2026-02-05
**Domain:** Technical documentation, README structure, developer tool positioning
**Confidence:** HIGH

## Summary

This phase requires rebranding CocoSearch's README from "semantic code search" to reflect its complete v1.8 feature set: hybrid search (semantic + keyword fusion), symbol filtering, context expansion, and stats dashboard observability. Research reveals that modern developer tools in 2026 prioritize action-oriented quick starts, clear capability positioning without feature-count competition, and honest tiering of language support. The current 1043-line README already has strong structure but needs repositioning at the top, feature hierarchy rebalancing, and integration of Phase 35's observability capabilities.

**Current State Analysis:**
- README is 1043 lines with comprehensive documentation
- Tagline emphasizes "Local-first semantic code search via MCP"
- Has 31 languages (5 symbol-aware: Python, JavaScript, TypeScript, Go, Rust)
- Stats dashboard implemented (Phase 35) but not prominently featured
- Structure: Intro → Architecture → Table of Contents → Installation → Usage → Features → Troubleshooting → Config

**Primary recommendation:** Lead with hybrid search positioning, reorganize to Quick Start immediately after tagline, create dedicated "Observability" section for stats/dashboard, tier languages explicitly (Full vs Basic support based on symbol awareness), maintain friendly tone but emphasize practical capabilities over marketing claims.

## Standard Stack

### Core Documentation Format
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Markdown | N/A | README format | Universal GitHub/Git standard, human-readable |
| Mermaid | N/A | Architecture diagrams | Native GitHub rendering, code-as-diagram |

### Supporting Tools
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| shields.io | N/A | Status badges | Show build status, version, license if desired |
| Table of Contents | N/A | Navigation | Required for docs >500 lines |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single README | Separate docs/ | Current README works well; moving to docs/ would require restructure |
| Markdown tables | HTML tables | Markdown simpler, more maintainable for language lists |

**Installation:**
No installation required - documentation editing uses standard Git workflow.

## Architecture Patterns

### Recommended README Structure for Developer Tools (2026)

Based on research from [Make a README](https://www.makeareadme.com/) and [FreeCodeCamp Structure Guide](https://www.freecodecamp.org/news/how-to-structure-your-readme-file/):

```
1. Project Title + Tagline (concise, value-focused)
2. Quick Start (installation + basic usage, 5 minutes or less)
3. What It Does (2-3 paragraphs, core capabilities)
4. Architecture/How It Works (optional diagram)
5. Table of Contents (for long docs)
6. Installation (detailed)
7. Usage (CLI/MCP/both)
8. Features (detailed capabilities)
9. Configuration
10. Contributing
11. License
```

### Pattern 1: Hybrid Search Positioning

**What:** Leading with "Hybrid search for codebases" positions the tool by its most powerful capability.

**When to use:** Primary tagline, feature list ordering, differentiation from pure semantic tools.

**Terminology from Meilisearch research:**
- "Hybrid search combines keyword-based retrieval (sparse vectors) with semantic search (dense vector embeddings)"
- Emphasize practical advantages: "exact identifier matching + semantic understanding"
- Frame as combining "lexical matching with contextual relevance"

**Example structure:**
```markdown
# CocoSearch

Hybrid search for codebases — semantic understanding meets keyword precision.

Index your code, search with natural language, filter by symbols. Works as CLI or MCP server. Everything runs locally.
```

### Pattern 2: Language Support Tiering

**What:** Explicitly tier languages by support level (Full vs Basic).

**When to use:** When tool has varying capability levels across languages.

**Best practice from Azure Functions research:**
- Full Support: Feature-complete (hybrid search + symbol filtering + context expansion)
- Basic Support: Indexed for semantic search, no symbol extraction

**Example:**
```markdown
## Supported Languages

### Full Support (Symbol-Aware)
Python, JavaScript, TypeScript, Go, Rust

**Capabilities:** Hybrid search, symbol filtering (--symbol-type, --symbol-name), smart context expansion

### Basic Support
C, C++, C#, Java, Ruby, Shell, SQL, YAML, JSON, Markdown, and 20+ more

**Capabilities:** Hybrid search, semantic search, keyword search
```

### Pattern 3: Observability Section Placement

**What:** Dedicated section for stats/dashboard features, positioned after core usage but before configuration.

**When to use:** When tool provides observability/monitoring capabilities.

**Research from OpenObserve and observability platforms (2026):**
- Stats dashboards are critical for DevOps workflows
- Position as operational feature, not secondary
- Include both CLI and visual dashboard options

**Example structure:**
```markdown
## Observability

Monitor index health, language distribution, and symbol breakdown.

### CLI Stats
```bash
cocosearch stats myproject --pretty
```

### Language Breakdown
[show per-language file/chunk/line counts]

### Dashboard
```bash
cocosearch serve-dashboard
# or integrated with MCP server
```
```

### Pattern 4: Quick Start Optimization

**What:** Place Quick Start immediately after tagline, before architecture/deep explanations.

**When to use:** Always, for developer tools.

**Research from Semantic Code Search README:**
- "TL;DR" section at top
- Installation + first search in < 5 minutes
- Technical explanation comes later

**Example:**
```markdown
# CocoSearch

Hybrid search for codebases.

## Quick Start (5 minutes)

**Docker (recommended):**
[3-step quick start]

**Local setup:**
[link to detailed installation]

**First search:**
```bash
cocosearch search "authentication logic"
```
```

### Anti-Patterns to Avoid

- **Feature list before action:** Users need Quick Start first, comprehensive feature list later
- **Marketing claims without proof:** "Best search" or "Most accurate" without benchmarks - let capabilities speak
- **Architecture before usage:** Save diagrams/technical depth for after Quick Start
- **Comparison sections:** Research shows "let features speak for themselves" approach works better in 2026
- **Troubleshooting in main flow:** Current README has this; consider moving to end or separate doc

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status badges | Custom HTML/SVG badges | shields.io | Standard, auto-updating, trusted |
| Table of Contents | Manual section links | Auto-generated ToC or clear structure | Maintenance burden |
| Architecture diagrams | Image files (PNG/JPG) | Mermaid code blocks | Version control friendly, editable as code |
| Multi-transport docs | Separate READMEs per client | Single README with clear sections | DRY principle, easier maintenance |

**Key insight:** Documentation maintenance is a hidden cost. Choose patterns that update easily when code changes (Mermaid diagrams, shields.io badges, inline examples from real code).

## Common Pitfalls

### Pitfall 1: Feature Creep in README

**What goes wrong:** As features are added (Phases 27-35: hybrid search, symbol filtering, context expansion, stats), the README becomes a linear append-only document without strategic reorganization.

**Why it happens:** Each phase adds documentation for its feature, but tagline/positioning stays anchored to original vision ("semantic code search").

**How to avoid:**
1. Reposition tagline to match current capabilities
2. Reorder feature hierarchy (hybrid search first, semantic component second)
3. Consolidate related sections (all search features together)
4. Move troubleshooting to end

**Warning signs:** Tagline doesn't match primary feature; new features buried in middle sections; feature list order doesn't match importance.

### Pitfall 2: Unclear Language Support Boundaries

**What goes wrong:** Users expect symbol filtering to work across all 31 languages, discover it only works for 5, feel misled.

**Why it happens:** Language list shows all supported extensions but doesn't tier by capability level.

**How to avoid:**
1. Explicit "Full Support" vs "Basic Support" sections
2. Symbol column in language table (✓/✗ indicator)
3. Note explaining what symbol-aware means
4. Link to `cocosearch languages` command for full list

**Warning signs:** User questions about "why doesn't --symbol-type work for Java"; GitHub issues about "missing features" that are actually tier-limited.

### Pitfall 3: Hidden Observability Features

**What goes wrong:** Phase 35 added comprehensive stats/dashboard but isn't discoverable in README positioning.

**Why it happens:** Stats added as management feature rather than promoted as core capability.

**How to avoid:**
1. Add "Observability" section at same level as "Search Features"
2. Mention stats in tagline context ("monitor index health")
3. Include language breakdown example in features
4. Link dashboard to MCP integration section

**Warning signs:** Users don't know stats exist; dashboard mentioned only in CLI Reference; no visual examples of observability output.

### Pitfall 4: Contributing Section Absence

**What goes wrong:** Open source project lacks Contributing section, signals project isn't welcoming to contributors.

**Why it happens:** Focus on user-facing documentation, developer contribution guidance overlooked.

**How to avoid:**
1. Add "Contributing" section after main documentation
2. Link to CONTRIBUTING.md if it exists, or inline basic guidelines
3. Include: setup instructions, coding standards, PR process
4. Mention Code of Conduct if present

**Warning signs:** No Contributing section; users unsure how to report bugs or submit PRs; contribution activity low despite GitHub stars.

## Code Examples

Since this is a documentation rebrand rather than code implementation, examples are documentation patterns rather than code.

### Tagline Evolution

**Current:**
```markdown
# CocoSearch

Local-first semantic code search via MCP. Search your codebase using natural language, entirely offline.
```

**Recommended (Per CONTEXT decisions):**
```markdown
# CocoSearch

Hybrid search for codebases — semantic understanding meets keyword precision.

Search your code with natural language, filter by symbols, expand context. Works as CLI or MCP server. Everything runs locally.
```

**Analysis:**
- Leads with "Hybrid search" (primary capability)
- "semantic understanding meets keyword precision" differentiates from pure semantic tools
- "filter by symbols, expand context" showcases v1.7/v1.8 features
- "CLI or MCP server" frames equal citizenship
- "Everything runs locally" positions privacy as secondary benefit, not primary pitch

### Language Tiering Example

**From `cocosearch languages` output:**
```
Symbol-aware: Python, JavaScript, TypeScript, Go, Rust (5/31)
Basic support: C, C++, C#, CSS, Fortran, HTML, Java, JSON, Kotlin, Markdown, Pascal, PHP, R, Ruby, Scala, Shell, Solidity, SQL, Swift, TOML, XML, YAML, Bash, Dockerfile, HCL (26/31)
```

**Recommended documentation:**
```markdown
## Supported Languages

CocoSearch indexes 31 programming languages via Tree-sitter. Language support tiers:

### Full Support (Symbol-Aware)
**Python**, **JavaScript**, **TypeScript**, **Go**, **Rust**

All features: Hybrid search, symbol filtering (`--symbol-type`, `--symbol-name`), smart context expansion

### Basic Support
C, C++, C#, CSS, Fortran, HTML, Java, JSON, Kotlin, Markdown, Pascal, PHP, R, Ruby, Scala, Shell, Solidity, SQL, Swift, TOML, XML, YAML, Bash, Dockerfile, HCL

Features: Hybrid search, semantic + keyword search, fixed context lines

View all extensions: `cocosearch languages`
```

### Observability Section Example

**Based on Phase 35 implementation:**
```markdown
## Observability

Monitor index health, language distribution, and symbol breakdown.

### Index Statistics

```bash
cocosearch stats myproject --pretty
```

Output:
```
    Index: myproject
┏━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric  ┃ Value     ┃
┡━━━━━━━━━╇━━━━━━━━━━━┩
│ Files   │ 42        │
│ Chunks  │ 127       │
│ Size    │ 2.3 MB    │
└─────────┴───────────┘
```

### Language Breakdown

```bash
cocosearch stats myproject --pretty
```

Shows per-language file counts, chunk distribution, and line counts.

### Dashboard (Coming Soon)

Visual stats dashboard via `cocosearch serve-dashboard` or integrated MCP server.
```

**Note:** "Coming Soon" if Phase 35 dashboard UI not yet complete; update when implemented.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure semantic search positioning | Hybrid search positioning | Phase 27 (v1.7) | Tagline must reflect hybrid, not just semantic |
| No language tiering | Explicit Full/Basic support tiers | Phase 29 (symbol extraction) | Need to document capability boundaries |
| Stats as management tool | Observability as feature | Phase 35 (v1.8) | Requires dedicated section, not just CLI ref |
| MCP primary, CLI secondary | Equal citizenship | CONTEXT decisions | Documentation must balance both equally |
| Troubleshooting prominent | Troubleshooting de-emphasized | 2026 doc trends | Move to end or separate doc per CONTEXT |

**Deprecated/outdated:**
- "Semantic code search" as primary positioning (accurate but incomplete)
- Flat language list without capability tiers (misleading for symbol filtering)
- Architecture diagram before Quick Start (slows time-to-first-success)

## Open Questions

### 1. Badge Strategy

**What we know:**
- Badges provide at-a-glance status (build, version, license)
- Research from shields.io and [repo-badges project](https://github.com/dwyl/repo-badges) shows 2026 best practice
- CONTEXT marks this as "Claude's discretion"

**What's unclear:**
- Does CocoSearch have CI/CD that supports build status badges?
- Is version badge desired (would require GitHub releases or PyPI)?
- Should Docker image version be badged?

**Recommendation:**
- Start minimal: License badge (AGPL-3.0) if present
- Add build status badge if CI exists
- Consider adding badge after project stability increases

### 2. Language Tier Terminology

**What we know:**
- 5 languages have symbol extraction (Python, JS, TS, Go, Rust)
- 26 languages have basic indexing
- CONTEXT says "Claude's discretion" for tiering terminology

**What's unclear:**
- "Full" vs "Basic" support?
- "Symbol-Aware" vs "Standard" support?
- "Advanced" vs "Standard" features?

**Recommendation:** "Full Support" and "Basic Support" because:
- Clear to non-technical users
- No negative connotation ("Standard" implies Basic is sub-standard)
- Common pattern in Azure Functions, Visual Studio docs

### 3. Differentiation Angle

**What we know:**
- CONTEXT says "Claude's discretion" for differentiation angle
- Options: semantic understanding, all-in-one, context-aware
- Research shows 2026 trend: let features speak, avoid comparisons

**What's unclear:**
- Which angle resonates with target users?
- How much to emphasize local/privacy vs hybrid/capabilities?

**Recommendation:** "All-in-one" angle:
- "Hybrid search + symbol filtering + context expansion + observability"
- Positions as complete solution, not just search
- Avoids comparison claims, focuses on capability combination
- Aligns with research showing "combination of capabilities" matters more than superlatives

### 4. Quick Start Positioning

**What we know:**
- CONTEXT says "After tagline: Quick start"
- Current README has Quick Start after "What CocoSearch Does" and Architecture
- Research shows Quick Start should be immediate

**What's unclear:**
- Should "What CocoSearch Does" (2-3 paragraph description) come before or after Quick Start?
- Should Architecture diagram come after Quick Start?

**Recommendation:**
```
1. Tagline
2. Quick Start (5 minutes)
3. What It Does (conceptual overview)
4. Architecture (diagram)
5. Table of Contents
[rest of docs]
```

Rationale: Get users to success ASAP (Quick Start first), then explain concepts (What/How).

## Sources

### Primary (HIGH confidence)
- Current README.md analysis - Complete structure, 1043 lines, 31 sections
- Phase 35 (Stats Dashboard) CONTEXT.md - Observability feature decisions
- Phase 37 (Documentation Rebrand) CONTEXT.md - User decisions and constraints
- `cocosearch languages` output - 31 languages, 5 symbol-aware confirmed
- `cocosearch management/stats.py` source code - Stats implementation verified

### Secondary (MEDIUM confidence)
- [Make a README](https://www.makeareadme.com/) - README structure best practices
- [FreeCodeCamp: How to Structure Your README](https://www.freecodecamp.org/news/how-to-structure-your-readme-file/) - Section ordering guidance
- [Medium: README Rules - Structure, Style, and Pro Tips](https://medium.com/@fulton_shaun/readme-rules-structure-style-and-pro-tips-faea5eb5d252) - Modern README patterns
- [GitHub: modelcontextprotocol/servers README](https://github.com/modelcontextprotocol/servers/blob/main/README.md) - MCP server documentation patterns
- [Sturdy Dev: Semantic Code Search README](https://github.com/sturdy-dev/semantic-code-search) - Similar tool positioning
- [Meilisearch: Hybrid Search Blog](https://www.meilisearch.com/blog/hybrid-search) - Hybrid search terminology and explanation
- [Daily.dev: Readme Badges GitHub Best Practices](https://daily.dev/blog/readme-badges-github-best-practices) - Badge strategy 2026
- [GitHub: repo-badges](https://github.com/dwyl/repo-badges) - Badge implementation guidance
- [Strategic Nerds: Developer Marketing Guide 2026](https://www.strategicnerds.com/blog/the-complete-developer-marketing-guide-2026) - Positioning strategy
- [DZone: Developer Tools That Actually Matter in 2026](https://dzone.com/articles/developer-tools-that-actually-matter-in-2026) - Differentiation principles
- [OpenObserve: Observability Dashboards](https://openobserve.ai/blog/observability-dashboards/) - Dashboard documentation patterns
- [Azure Functions: Supported Languages](https://learn.microsoft.com/en-us/azure/azure-functions/supported-languages) - Language tiering examples
- [Open Source Guides: How to Contribute](https://opensource.guide/how-to-contribute/) - Contributing section best practices
- [Mozilla Science: CONTRIBUTING.md Guide](https://mozillascience.github.io/working-open-workshop/contributing/) - Contributing guidelines

### Tertiary (LOW confidence)
- Web search results on "README best practices 2026" - General guidance, not tool-specific
- Web search results on "hybrid search positioning" - Industry trends, not CocoSearch-specific

## Metadata

**Confidence breakdown:**
- Current state analysis: HIGH - Direct source code and README inspection
- Standard stack: HIGH - Markdown/Mermaid are universal standards
- Architecture patterns: HIGH - Multiple authoritative sources (Make a README, FreeCodeCamp, MCP servers)
- Language tiering: MEDIUM - Inferred from symbol-aware detection, not explicit user research
- Differentiation strategy: MEDIUM - Based on 2026 trends research, not user testing
- Observability positioning: HIGH - Phase 35 CONTEXT confirms decisions

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - documentation standards stable, developer tool trends slow-moving)

**Key constraints from CONTEXT.md:**
- Tagline must lead with "Hybrid search for codebases"
- MCP and CLI equal citizenship (no prioritization)
- Contributing section required
- No Troubleshooting in main flow (move to end or remove)
- Friendly and approachable tone
- Examples use real code (CocoSearch or well-known repos)
- No comparison section

**Claude's discretion areas:**
- Exact tagline wording (must include "Hybrid search")
- Differentiation angle (recommend: all-in-one capabilities)
- Language tier terminology (recommend: Full/Basic Support)
- Section ordering within constraints
- Badge inclusion (recommend: minimal/none initially)
