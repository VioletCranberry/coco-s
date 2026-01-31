---
phase: 18
plan: 01
subsystem: documentation
completed: 2026-01-31
duration: 6m
type: execute

requires:
  - 15-01  # Config schema with camelCase fields
  - 16-02  # CLI with config discovery
  - 17-01  # Developer setup script

provides:
  - cocosearch.yaml dogfooding config (indexName: self)
  - README section demonstrating CocoSearch searching itself
  - Example searches showing architecture and implementation queries
  - Verification workflow with stats command

affects:
  - New contributors can immediately see CocoSearch value
  - Dogfooding workflow validated for v1.4

tech-stack:
  added: []
  patterns:
    - "Self-referential documentation (dogfooding)"
    - "Minimal configuration demonstrating defaults"
    - "Annotated CLI examples with sample output"

key-files:
  created:
    - cocosearch.yaml
  modified:
    - README.md

decisions:
  - id: DOGF-CONFIG-MINIMAL
    phase: 18-01
    what: Keep cocosearch.yaml minimal (only indexName and includePatterns)
    why: Demonstrates that CocoSearch defaults work well without extensive configuration
    impact: Users see they can trust defaults, lowering barrier to entry

  - id: DOGF-EXAMPLE-MIX
    phase: 18-01
    what: Mix architecture and implementation queries in README examples
    why: Shows CocoSearch handles both high-level and code-level questions
    impact: Broader demonstration of tool capabilities

  - id: DOGF-STANDALONE-COMMANDS
    phase: 18-01
    what: Use "uv run cocosearch" in all examples (not bare "cocosearch")
    why: Doesn't assume user ran dev-setup.sh or has environment configured
    impact: Examples are copy-pasteable from any state

  - id: DOGF-ANNOTATED-OUTPUT
    phase: 18-01
    what: Show truncated, annotated output (not full dumps) in README
    why: Balances showing value vs maintaining readable documentation
    impact: Users understand what results look like without overwhelming detail

tags:
  - dogfooding
  - documentation
  - configuration
  - onboarding
  - self-referential
  - examples
---

# Phase 18 Plan 01: Dogfooding Configuration Summary

**One-liner:** Created cocosearch.yaml for indexing CocoSearch itself and added README section with 4 example searches demonstrating architecture and implementation queries.

## What Was Built

This plan completed the dogfooding story for v1.4 by creating a self-referential configuration and documentation that demonstrates CocoSearch's value through actual usage on its own codebase.

### Key Artifacts

1. **cocosearch.yaml** - Minimal dogfooding configuration at repository root
   - Index name: `self` (meta - it indexes itself)
   - Include patterns: Python, Bash, Docker, Markdown files
   - Implicitly includes test files (useful for finding test patterns)
   - Relies on defaults for excludePatterns and chunk settings
   - Demonstrates that minimal configuration works well

2. **README.md "Searching CocoSearch" section** - Practical demonstration after Quick Start
   - Prerequisites (Docker + Python 3.12+ with uv)
   - Indexing command with expected output
   - Verification step: `uv run cocosearch stats self --pretty`
   - 4 example searches with annotated output:
     - **Embedding implementation** - Architecture query finding OllamaEmbedder class
     - **Database operations** - Implementation query finding connection handling
     - **Docker setup** - DevOps query with `--lang bash` filter finding dev-setup.sh
     - **Config discovery** - System query finding configuration loader logic
   - Cross-reference to dev-setup.sh for full environment setup
   - Table of Contents updated to include new section

### Implementation Details

**Config Field Naming:**
- Used camelCase consistently (indexName, includePatterns) per schema.py
- NOT snake_case (index_name, include_patterns)
- Critical for Pydantic validation to succeed

**Example Command Pattern:**
- All examples use `uv run cocosearch` (standalone)
- Doesn't assume user ran dev-setup.sh
- Makes examples copy-pasteable from any state

**Output Annotations:**
- Truncated output showing first match with score
- Enough context to understand what was found
- Not full dumps (maintains documentation readability)

**Language Filtering:**
- Included --lang example (Docker setup filtered to Bash)
- Demonstrates language-specific search capability

## Decisions Made

### DOGF-CONFIG-MINIMAL
Keep cocosearch.yaml minimal with only indexName and includePatterns, relying on defaults for excludePatterns and chunk settings. This demonstrates that CocoSearch works well out-of-box without extensive configuration, lowering the barrier to entry for new users.

### DOGF-EXAMPLE-MIX
Mix architecture questions ("how does embedding work") with implementation queries ("database connection handling") in README examples. This shows CocoSearch handles both high-level conceptual questions and specific code-level searches, demonstrating broader tool capabilities.

### DOGF-STANDALONE-COMMANDS
Use "uv run cocosearch" format in all README examples instead of bare "cocosearch" commands. This doesn't assume users have run dev-setup.sh or configured their environment, making examples immediately copy-pasteable from any state.

### DOGF-ANNOTATED-OUTPUT
Show truncated, annotated output in README examples rather than full result dumps. This balances showing users what results look like with maintaining readable documentation that doesn't overwhelm with detail.

## Deviations from Plan

None - plan executed exactly as written.

## Challenges & Solutions

No significant challenges. The configuration system (Phase 15), CLI (Phase 16), and dev-setup.sh (Phase 17) were complete, making this a straightforward documentation task.

**Minor consideration:** Ensured camelCase field naming in YAML (indexName, includePatterns) matches schema.py to avoid validation errors. Research documentation explicitly warned about this pitfall.

## Testing & Verification

**Config validation:**
```bash
uv run python -c "import yaml; y=yaml.safe_load(open('cocosearch.yaml')); print(y)"
# Output: {'indexName': 'self', 'indexing': {'includePatterns': [...]}}
```

**README verification:**
- Section exists at line 80: `grep -n "## Searching CocoSearch" README.md`
- TOC updated: `grep "Searching CocoSearch" README.md` shows 2 references (TOC + section)
- Language filter example exists: `grep "\-\-lang" README.md` shows usage
- Section placement: After Quick Start (line 49), before Installation (line 192)

**Success criteria met:**
- ✅ cocosearch.yaml exists with indexName: self and includePatterns for Python/DevOps/Markdown
- ✅ README.md contains "Searching CocoSearch" section after Quick Start
- ✅ Table of Contents updated to include new section
- ✅ Example commands use standalone `uv run cocosearch` format
- ✅ At least one example shows --lang flag usage (Docker setup example)
- ✅ Section references dev-setup.sh for full environment setup

## Files Changed

**Created:**
- `cocosearch.yaml` - Dogfooding configuration (11 lines)

**Modified:**
- `README.md` - Added "Searching CocoSearch" section (+113 lines), updated TOC

**Commits:**
- 9a53669: feat(18-01): add dogfooding configuration
- 0f40d76: docs(18-01): add Searching CocoSearch section to README

## Key Learnings

**Dogfooding as demonstration:**
Self-referential examples are more compelling than contrived demos. By using CocoSearch to search CocoSearch, new contributors immediately see authentic usage and can verify the tool's capabilities before committing to setup.

**Minimal config philosophy:**
Showing what you DON'T need to configure is as important as showing what you can configure. The minimal cocosearch.yaml (just indexName + includePatterns) demonstrates trust in defaults.

**Standalone commands in docs:**
Documentation examples should work from any state. Using `uv run cocosearch` instead of assuming environment setup makes examples immediately usable, reducing friction for new users.

**Output annotation balance:**
Truncated, annotated output (first match with score) is better than full dumps or no output. Users need enough context to understand value without being overwhelmed by detail.

## Next Phase Readiness

**Phase 18 Status:**
- Plan 01 complete (dogfooding config and README)
- Plan 02 remaining (manual dogfooding validation checkpoint)

**Next Steps:**
Execute 18-02-PLAN.md to perform manual dogfooding validation:
- Index CocoSearch codebase using cocosearch.yaml
- Verify stats output matches expectations
- Run example searches from README and confirm results
- Human checkpoint to approve dogfooding experience

**No blockers or concerns.**

## References

- Phase 15: Configuration System (schema.py defines camelCase fields)
- Phase 16: CLI Config Integration (config discovery in all commands)
- Phase 17: Developer Setup Script (referenced for full environment setup)
- 18-CONTEXT.md: Implementation decisions (minimal config, standalone commands)
- 18-RESEARCH.md: Patterns (self-referential docs, annotated examples)

---

**Duration:** 6 minutes
**Deviations:** None
**Status:** ✅ Complete
