---
phase: 36-developer-skills
plan: 01
subsystem: documentation
status: complete
tags: [claude-code, skills, mcp, developer-tools]

dependency-graph:
  requires: [35-stats-dashboard]
  provides: [claude-code-skill-documentation]
  affects: [36-02-opencode-skill]

tech-stack:
  added: []
  patterns: [skill-documentation-format]

files:
  created:
    - .claude/skills/cocosearch/SKILL.md
  modified: []

decisions:
  - decision: Force-add .claude directory despite global gitignore
    rationale: Skill file is project documentation (template/example), not user-local config
    impact: Enables sharing skill documentation with users via repository
    alternatives: Move to docs/ directory (rejected - violates Claude Code conventions)

metrics:
  duration: 2min
  completed: 2026-02-05
---

# Phase 36 Plan 01: Claude Code Skill Summary

**One-liner:** Claude Code skill with MCP stdio config, decision tree routing, and 6 workflow examples

## What Was Built

Created `.claude/skills/cocosearch/SKILL.md` - comprehensive skill documentation for Claude Code users to:
- Install CocoSearch via UV
- Configure MCP server (CLI or JSON methods)
- Understand when to use CocoSearch vs grep/ripgrep vs IDE tools
- Reference 6 workflow examples with expected output

**Key capabilities:**
- Quick setup instructions (UV + CocoSearch installation)
- MCP configuration for stdio transport (both `claude mcp add` CLI and `~/.claude.json` methods)
- Decision tree: semantic queries → CocoSearch, exact matches → grep, refactoring → IDE
- 6 workflow examples covering semantic discovery, hybrid search, symbol filters, context expansion, language filters, and combined filters
- Anti-patterns section to avoid misuse
- README reference for advanced troubleshooting

## Decisions Made

1. **Force-add .claude directory despite global gitignore**
   - **Context:** User's global gitignore excludes `.claude/` (standard for IDE-like configs)
   - **Decision:** Use `git add -f` to commit skill file as project artifact
   - **Rationale:** Skill is project documentation/template for users, not personal configuration
   - **Impact:** Users can reference in-repo skill file for setup guidance

2. **Include 6 examples instead of minimum 5**
   - **Context:** Plan specified "5+ examples"
   - **Decision:** Included semantic, hybrid, context, language, symbol name, and combined filter examples
   - **Rationale:** Covers all major use cases, demonstrates power of combined flags
   - **Impact:** More comprehensive guidance, slight increase to 172 lines (acceptable)

3. **Keep Troubleshooting section as pointer only**
   - **Context:** 36-CONTEXT.md says "no troubleshooting sections"
   - **Decision:** Include section header with README reference only
   - **Rationale:** Fulfills "reference README for troubleshooting" without duplicating content
   - **Impact:** Maintains focus, defers deep troubleshooting to README

## Technical Implementation

**File structure:**
```
.claude/skills/cocosearch/SKILL.md (172 lines)
├── Frontmatter (name, description)
├── Quick Setup (~12 lines)
├── MCP Configuration (~45 lines: CLI + JSON + verification)
├── When to Use (~22 lines: decision tree)
├── Workflow Examples (~60 lines: 6 examples with output)
├── Anti-Patterns (~10 lines)
└── Troubleshooting (~5 lines: README pointer)
```

**Decision tree structure:**
- **Use CocoSearch for:** Intent-based discovery, symbol exploration, cross-file patterns, context expansion, semantic queries
- **Use grep/ripgrep for:** Exact identifiers, regex, known locations, string literals, fast exhaustive search
- **Use IDE tools for:** Go-to-definition, find-references, rename refactoring, type/call hierarchies

**MCP configuration patterns:**
- Option A: CLI with `claude mcp add --transport stdio` (recommended)
- Option B: JSON in `~/.claude.json` (manual alternative)
- Both use UV's `--directory` flag for project isolation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Global gitignore excludes .claude directory**
- **Found during:** Task 1 commit attempt
- **Issue:** User's `~/.gitignore-global` contains `.claude/` exclusion, blocking `git add`
- **Fix:** Used `git add -f` to force-add skill file as project artifact
- **Files modified:** .claude/skills/cocosearch/SKILL.md
- **Commit:** 9374251
- **Rationale:** Plan explicitly lists file in `files_modified` and `artifacts` - intent is to commit as documentation

## Testing & Verification

**Structure validation:**
- ✓ Valid YAML frontmatter with concise description
- ✓ MCP configuration includes both CLI and JSON options
- ✓ Decision tree with explicit routing guidance (3 tool categories)
- ✓ 6 workflow examples with commands and expected output
- ✓ README reference for troubleshooting (no content duplication)
- ✓ Compact format (172 lines, bullet-point style)

**Content validation:**
- ✓ `grep "mcpServers"` matches JSON config
- ✓ `grep -c "cocosearch search"` returns 6 (examples count)
- ✓ `grep "README"` confirms troubleshooting reference
- ✓ Decision tree covers semantic/exact/refactoring scenarios

## Next Phase Readiness

**Completed:**
- Claude Code skill structure established (template for 36-02 OpenCode skill)
- Skill documentation pattern validated (compact, decision tree, examples with output)

**Blockers:** None

**Concerns/Research flags:**
- Line count is 172 vs target ~100 (acceptable - example output adds value)
- Test skill with Claude Code users to verify routing decision tree effectiveness (phase 36 research flag)

## Artifacts

**Created:**
- `.claude/skills/cocosearch/SKILL.md` (172 lines) - Claude Code skill documentation

**Modified:** None

**Git history:**
```
9374251 docs(36-01): create Claude Code skill for CocoSearch
```

---

*Phase: 36-developer-skills*
*Plan: 01 of 3*
*Completed: 2026-02-05*
