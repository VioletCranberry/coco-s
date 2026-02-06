---
phase: 41-workflow-skills
plan: 03
subsystem: developer-tools
tags: [refactoring, semantic-search, mcp, workflow, dependency-analysis]

# Dependency graph
requires:
  - phase: 41-01
    provides: CocoOnboarding workflow skill with MCP tool patterns
  - phase: 41-02
    provides: CocoDebugging workflow skill with adaptive branching
provides:
  - CocoRefactoring workflow skill with full impact analysis
  - Safe refactoring execution with user confirmation gates
  - Leaf-first dependency ordering pattern
  - Index staleness detection for refactoring tasks
affects: [41-04-skill-discovery, documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Impact analysis workflow: usages + test coverage + downstream effects"
    - "Leaf-first refactoring execution order (callees before callers)"
    - "User confirmation gates before every code change"
    - "Adaptive branching based on impact level (low/medium/high)"

key-files:
  created:
    - skills/coco-refactoring/SKILL.md
  modified: []

key-decisions:
  - "Require fresh index (staleness_days <= 7) for refactoring - unlike debugging/onboarding"
  - "Use hybrid search for all refactoring searches (identifier-heavy queries)"
  - "Use symbol_name glob patterns to catch all variants (User* catches User, UserProfile, etc.)"
  - "Leaf-first ordering prevents cascading import failures"
  - "Every code change requires explicit user confirmation"
  - "Suggest testing after each change, not just at end"

patterns-established:
  - "Impact analysis structure: direct usages → test coverage → downstream effects → risk assessment"
  - "Execution gate pattern: show preview → request confirmation → make change → verify → next step"
  - "Refactoring plan structure: create new → migrate → update deps → update tests → remove old"

# Metrics
duration: 2min
completed: 2026-02-06
---

# Phase 41 Plan 03: CocoRefactoring Skill Summary

**Complete refactoring workflow skill with semantic impact analysis, leaf-first execution ordering, and user confirmation gates at every code change**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-06T09:46:37Z
- **Completed:** 2026-02-06T09:48:38Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Created refactoring workflow skill with 313 lines of systematic guidance
- Implemented full impact analysis: all usages + test coverage + downstream effects mapping
- Established leaf-first execution ordering pattern (callees before callers for safety)
- Built adaptive branching based on impact level (low/medium/high risk assessment)
- Added user confirmation gates before every code change
- Integrated index staleness detection (require fresh index for refactoring tasks)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create refactoring workflow skill** - `ed45c9f` (feat)

**Task 2: Validate refactoring skill completeness** - No commit (validation only, all checks passed)

**Plan metadata:** (pending - see final commit below)

## Files Created/Modified
- `skills/coco-refactoring/SKILL.md` - Refactoring workflow skill with impact analysis and safe execution

## Decisions Made

**Refactoring-specific requirements:**
- Fresh index required (staleness_days <= 7) - unlike debugging/onboarding workflows, refactoring needs 100% accurate dependency data
- If no index exists, indexing is REQUIRED before proceeding (not optional)

**Search strategy:**
- Use hybrid search for all refactoring queries (identifier-heavy, need exact + semantic)
- Use symbol_name with glob patterns to catch all variants (e.g., "User*" finds User, UserProfile, UserService)
- Use smart_context=True to see full function/class bodies for understanding dependencies

**Execution safety:**
- Leaf-first ordering: change callees before callers, create before migrate, update before remove
- Every code change requires explicit user confirmation (yes/no/skip)
- Suggest running tests after each change, not just at the end
- STOP on test failure, show details, ask user how to proceed

**Impact analysis structure:**
- Step 2a: Find all usages (direct symbol references + import references)
- Step 2b: Find test coverage (test files + coverage assessment)
- Step 2c: Find downstream effects (what depends on the callers)
- Step 2d: Present dependency map with risk assessment (low/medium/high)
- Step 2e: Branch based on impact (proceed / confirm scope / warn + suggest incremental)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - skill creation completed without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next phase:**
- Third workflow skill complete (onboarding, debugging, refactoring)
- All three skills follow consistent pattern: adaptive branching, auto-execute searches, user control
- Skills demonstrate full range of CocoSearch capabilities (discovery, impact analysis, dependency mapping)

**What's available:**
- skills/coco-onboarding/SKILL.md - New codebase understanding workflow
- skills/coco-debugging/SKILL.md - Bug investigation workflow with staleness detection
- skills/coco-refactoring/SKILL.md - Safe refactoring workflow with impact analysis

**Remaining for Phase 41:**
- Plan 04: Skill discovery mechanism (how users find and invoke skills)

---
*Phase: 41-workflow-skills*
*Completed: 2026-02-06*

## Self-Check: PASSED

All files and commits verified to exist.
