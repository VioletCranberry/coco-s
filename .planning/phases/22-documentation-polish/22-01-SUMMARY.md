---
phase: 22-documentation-polish
plan: 01
subsystem: documentation
tags: [readme, toc, navigation, structure]
requires:
  - phases: [21]
provides:
  - Professional README with comprehensive table of contents
  - User journey-oriented section organization
  - Enhanced documentation navigation
affects:
  - phases: [22-02, 22-03, 22-04]
    reason: "Further documentation improvements build on this structure"
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - README.md
decisions:
  - id: toc-with-emojis
    choice: Add unique emoji prefix to each top-level TOC section
    rationale: Visual distinction improves scannability and professional appearance
  - id: user-journey-order
    choice: Reorganize sections as overview -> install -> quick start -> dogfooding -> config -> advanced
    rationale: Matches natural user progression from discovery to advanced usage
  - id: action-oriented-headings
    choice: Rename sections to action-oriented style (Installing, Configuring, etc.)
    rationale: Makes sections more actionable and clear about what users will accomplish
  - id: back-to-top-links
    choice: Add back-to-top links after all 6 major sections
    rationale: Improves navigation in long README, allows quick return to TOC
metrics:
  duration: 137s
  completed: 2026-02-01
---

# Phase 22 Plan 01: README Table of Contents Summary

**One-liner:** Comprehensive TOC with emoji prefixes, user journey structure, and back-to-top navigation

## Objective

Reorganize README.md with comprehensive table of contents to enable professional navigation with clickable TOC entries, emoji prefixes, and user journey-oriented section flow.

## What Changed

### Added
- **Comprehensive table of contents** covering all H2 and H3 sections (6 major sections, 20 subsections)
- **Emoji prefixes** on top-level TOC entries:
  - 📦 Installing
  - 🚀 Getting Started
  - 🔍 Dogfooding
  - ⚙️ Configuring MCP
  - 💻 CLI Reference
  - 🛠️ Configuration
- **Back-to-top links** after all 6 major sections linking to `#table-of-contents`

### Modified
- **Section reorganization** following user journey:
  1. What CocoSearch Does (overview)
  2. Architecture (overview)
  3. Installing (setup)
  4. Getting Started (quick start)
  5. Dogfooding (example usage)
  6. Configuring MCP (integration)
  7. CLI Reference (advanced)
  8. Configuration (advanced)
- **Action-oriented headings:**
  - "Installation" → "Installing"
  - "Quick Start" → "Getting Started"
  - "Searching CocoSearch" → "Dogfooding"
  - "MCP Configuration" → "Configuring MCP"
- **Subsection reorganization** for clarity:
  - Installing: Ollama → PostgreSQL → CocoSearch
  - Getting Started: Index → Search → MCP
  - Dogfooding: Prerequisites → Index → Verify → Examples → Dev Environment
  - Configuring MCP: Claude Code → Claude Desktop → OpenCode
  - CLI Reference: Indexing → Searching → Managing

### Preserved
- All original content intact (no content deleted)
- All code examples unchanged
- All technical details maintained
- All links to external resources preserved

## Implementation Notes

### TOC Structure
- **Format:** Standard markdown anchor links `[Section Name](#section-name)`
- **Nesting:** 2-space indentation for H3 subsections under H2 sections
- **Coverage:** 100% of sections included (6 H2 + 20 H3 = 26 total entries)
- **No numbering:** Clean list without numbers for better readability

### Section Flow Rationale
The new order follows natural user progression:
1. **Overview** (What/Architecture) - Understand the value proposition
2. **Installation** - Get it running
3. **Getting Started** - First success with basic usage
4. **Dogfooding** - See real-world example with CocoSearch's own codebase
5. **Configuring MCP** - Integrate with AI assistants
6. **CLI Reference** - Deep dive into commands
7. **Configuration** - Advanced customization

### Anchor Link Strategy
- Emoji characters included in heading but NOT in anchor
- Anchor format: lowercase, spaces to hyphens, special chars removed
- Example: `## 📦 Installing` → `#-installing` (emoji becomes hyphen)

## Verification Results

✅ **TOC completeness:** All 6 H2 and 20 H3 headings present in TOC (26 entries)
✅ **Link functionality:** All TOC entries use valid markdown anchor syntax
✅ **Emoji presence:** All 6 top-level TOC entries have unique emoji prefixes
✅ **Section order:** Follows user journey: overview → install → quick start → dogfooding → config → advanced
✅ **Back-to-top:** 6 back-to-top links present after all major sections
✅ **Content preserved:** All original content maintained, only structure changed

Manual verification recommended:
- Click each TOC link in GitHub preview to confirm anchor navigation
- Verify back-to-top links jump to TOC
- Check emoji rendering across different markdown viewers

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Emoji selection:** Chose emojis that represent each section's purpose:
   - 📦 for Installing (package/setup)
   - 🚀 for Getting Started (launch/quick start)
   - 🔍 for Dogfooding (search/exploration)
   - ⚙️ for Configuring MCP (settings/configuration)
   - 💻 for CLI Reference (terminal/command line)
   - 🛠️ for Configuration (tools/customization)

2. **Major sections for back-to-top:** All 6 H2 sections qualified as "major" since README is long (615 lines) and each section is substantial

3. **Subsection naming:** Maintained specificity in subsection names rather than generic action verbs (e.g., "Configuring Claude Code" instead of just "Claude Code")

## Key Files Modified

### README.md
- **Lines changed:** 133 insertions, 102 deletions (net +31 lines)
- **Sections reordered:** 6 major sections moved to new positions
- **New elements:** 1 comprehensive TOC (26 entries) + 6 back-to-top links
- **Headings renamed:** 4 section headings made action-oriented

## Commit Record

| Task | Commit  | Message                                        |
|------|---------|------------------------------------------------|
| 1    | 5f6af14 | docs(22-01): restructure README with comprehensive TOC |

## Next Phase Readiness

**Ready for 22-02:** README structure is now optimized for navigation. Next plan can focus on content improvements knowing the structure is solid.

**No blockers:** All content preserved and reorganized successfully.

**Recommendations:**
- Test TOC links in GitHub's markdown preview to verify anchor navigation
- Consider user feedback on emoji choices (can be easily adjusted if needed)
- Monitor if any external links to README sections break (though old anchors may still work)

## Success Criteria Met

- [x] README.md has comprehensive Table of Contents
- [x] TOC covers all H2 and H3 sections (6 + 20 = 26 entries)
- [x] Top-level TOC entries have emoji prefixes (6 emojis)
- [x] Sections reordered for user journey flow
- [x] Headings use action-oriented style where applicable
- [x] Back-to-top links after major sections (6 links)
- [x] All TOC links are valid markdown anchors

---

**Duration:** 137 seconds (~2.3 minutes)
**Status:** Complete
**Quality:** All verification criteria passed
