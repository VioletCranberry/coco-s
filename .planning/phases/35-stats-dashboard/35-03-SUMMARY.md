---
phase: 35-stats-dashboard
plan: 03
subsystem: observability
tags: [web-ui, dashboard, chart.js, http, browser, visualization]

# Dependency graph
requires:
  - phase: 35-02
    provides: HTTP API endpoint /api/stats for web UI data fetching
provides:
  - Browser-accessible web dashboard at /dashboard with Chart.js visualizations
  - Dark/light mode auto-detection based on system preference
  - Standalone serve-dashboard CLI command for web server
  - Single-page HTML with embedded CSS/JS (no build step required)
affects: [36-skill-routing, web-monitoring, external-dashboards]

# Tech tracking
tech-stack:
  added: [chart.js, starlette.HTMLResponse]
  patterns: [single-page dashboard, embedded CSS/JS, CSS variables for theming, CDN-based charts]

key-files:
  created:
    - src/cocosearch/dashboard/web/__init__.py
    - src/cocosearch/dashboard/web/static/index.html
  modified:
    - src/cocosearch/mcp/server.py
    - src/cocosearch/cli.py

key-decisions:
  - "Single-page HTML with embedded CSS/JS (no build step, no bundler required)"
  - "Chart.js via CDN for zero-config setup and browser caching"
  - "CSS variables with prefers-color-scheme for automatic dark/light mode"
  - "Grafana-like dense layout: summary cards at top, charts below"
  - "Horizontal bar charts (indexAxis: 'y') for language distribution readability"
  - "serve-dashboard reuses MCP server infrastructure (no duplicate HTTP code)"
  - "HTMLResponse serving static content from dashboard/web/static/"
  - "Auto-refresh timestamp shows last data fetch time"

patterns-established:
  - "Web dashboard pattern: fetch /api/stats → display with Chart.js"
  - "get_dashboard_html() function returns HTML string from static file"
  - "Dashboard module exports: get_dashboard_html() for server integration"
  - "Index selector dropdown for multi-index installations"
  - "Warning banner pattern consistent across CLI/terminal/web interfaces"

# Metrics
duration: 12 min
completed: 2026-02-05
---

# Phase 35 Plan 03: Web Dashboard Summary

**Browser-accessible dashboard at /dashboard with Chart.js bar charts, automatic dark/light mode, and standalone serve-dashboard command**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-05T14:14:35Z
- **Completed:** 2026-02-05T14:26:46Z
- **Tasks:** 3 auto + 1 checkpoint + 2 bug fixes
- **Files modified:** 2 created, 2 modified

## Accomplishments

- Single-page HTML dashboard with embedded CSS and JavaScript (no build step required)
- Chart.js bar charts for language distribution (horizontal bars) and symbol types (vertical bars)
- Automatic dark/light mode detection via CSS prefers-color-scheme media query
- Grafana-like dense layout: summary cards (files, chunks, size, last update) at top, charts in grid below
- Warning banner displays prominently when index has health issues
- Index selector dropdown for switching between multiple indexes
- /dashboard route in MCP server serves HTML via HTMLResponse
- serve-dashboard CLI command starts standalone web server at configurable host:port
- Auto-refresh timestamp shows when data was last fetched
- Graceful error handling for missing metadata table (pre-metadata indexes)
- Fixed JSON output mode defaulting logic (visual output now default, --json explicit)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create web dashboard HTML with Chart.js** - `b0af04d` (feat)
   - dashboard/web/__init__.py with get_dashboard_html() function
   - dashboard/web/static/index.html (404 lines) with:
     - CSS variables for theming (:root and @media prefers-color-scheme: dark)
     - Header with title and index selector dropdown
     - Warning banner (hidden by default, shown if stats.warnings exists)
     - Summary stats grid (4 cards: files, chunks, size, last update)
     - Charts grid (2 charts: language distribution, symbol types)
     - Refresh timestamp footer
     - Chart.js from cdn.jsdelivr.net/npm/chart.js@4
     - JavaScript: loadStats() fetches /api/stats, displayStats() renders charts
     - Index selector change handler switches displayed stats

2. **Task 2: Add /dashboard route to MCP server** - `aa1fc83` (feat)
   - Import get_dashboard_html from cocosearch.dashboard.web
   - Import HTMLResponse from starlette.responses
   - @mcp.custom_route("/dashboard", methods=["GET"]) decorator
   - serve_dashboard() function returns HTMLResponse with HTML content
   - Updated /health endpoint docstring to mention /dashboard

3. **Task 3: Add serve-dashboard CLI command** - `cba9197` (feat)
   - serve-dashboard subparser with --port and --host flags
   - serve_dashboard_command() function:
     - Prints startup message with dashboard and API URLs
     - Calls run_server(transport="sse", host=args.host, port=args.port)
     - Handles KeyboardInterrupt for clean shutdown
     - Handles OSError for "Address already in use" error with clear message
   - Added to command routing and known_subcommands list

**Checkpoint verification and bug fixes:**

4. **Bug fix: Missing metadata table handling** - `2335e28` (fix)
   - Added exception handling in check_staleness() for missing cocosearch_index_metadata table
   - Added exception handling in get_comprehensive_stats() for graceful degradation on pre-metadata indexes
   - Fixed json_output logic in cli.py: visual output is default, --json flag enables JSON (was incorrectly inverted)
   - Refactored stats.py exception handling for cleaner error recovery

## Files Created/Modified

- `src/cocosearch/dashboard/web/__init__.py` (+8 lines) - Module exports get_dashboard_html()
- `src/cocosearch/dashboard/web/static/index.html` (+404 lines) - Single-page dashboard with Chart.js
- `src/cocosearch/mcp/server.py` (+12 lines) - /dashboard route serving HTML
- `src/cocosearch/cli.py` (+42 lines) - serve-dashboard command with --port and --host flags
- `src/cocosearch/management/stats.py` (+43 lines modified) - Exception handling for missing metadata table

## Decisions Made

1. **Single-page HTML with embedded CSS/JS** - Eliminates build step and bundler complexity; all code in one 404-line file for easy inspection and modification
2. **Chart.js via CDN** - Zero configuration required, browser caching, automatic updates, no npm dependencies
3. **CSS variables for theming** - Clean separation of colors, automatic dark/light mode via prefers-color-scheme media query
4. **Grafana-like dense layout** - Summary cards at top for quick metrics, charts in grid below for detailed exploration
5. **Horizontal language bars** - More readable than vertical bars for language names (Python, JavaScript, etc.)
6. **Reuse MCP server for serve-dashboard** - Avoids duplicate HTTP server code, leverages existing /api/stats and /dashboard routes
7. **HTMLResponse pattern** - Clean integration with FastMCP custom routes, consistent with existing patterns
8. **Auto-refresh timestamp** - User knows when data was last fetched, encourages manual refresh if stale

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing metadata table exception handling**
- **Found during:** Task 4 (checkpoint verification)
- **Issue:** check_staleness() and get_comprehensive_stats() crashed when cocosearch_index_metadata table didn't exist (pre-metadata indexes)
- **Fix:** Added try/except blocks in both functions to gracefully handle missing table; return None for updated_at and staleness_days=-1 on exception
- **Files modified:** src/cocosearch/management/stats.py
- **Verification:** CLI stats command works on pre-metadata indexes without crashing
- **Committed in:** 2335e28 (bug fix commit)

**2. [Rule 1 - Bug] JSON output mode logic inverted**
- **Found during:** Task 4 (checkpoint verification)
- **Issue:** --json flag logic was inverted; JSON output was default instead of visual output
- **Fix:** Changed `json_output = not args.json` to `json_output = args.json` in cli.py
- **Files modified:** src/cocosearch/cli.py
- **Verification:** `cocosearch stats` shows visual output, `cocosearch stats --json` shows JSON
- **Committed in:** 2335e28 (bug fix commit)

---

**Total deviations:** 2 auto-fixed (2 bugs discovered during verification)
**Impact on plan:** Both bugs critical for correctness. Missing metadata handling ensures backward compatibility with older indexes. JSON flag fix ensures correct default behavior.

## Issues Encountered

**Checkpoint verification revealed two bugs:**
1. Missing metadata table handling - Stats command crashed on pre-metadata indexes
2. JSON output defaulting incorrectly - Visual output should be default, not JSON

Both issues fixed in single commit (2335e28) following Rule 1 (auto-fix bugs).

## User Setup Required

None - no external service configuration required.

**For runtime usage:**
- PostgreSQL must be running for stats data
- Existing indexed projects required to display dashboard
- Browser required for web dashboard access
- Default port 8080 must be available (or use --port flag)

## Next Phase Readiness

**Ready for next phase.** Complete stats dashboard system with three interfaces:

1. **CLI interface:** `cocosearch stats` with visual output, Unicode bars, warnings
2. **Terminal dashboard:** `cocosearch stats --live` with htop-style multi-pane layout
3. **Web dashboard:** `cocosearch serve-dashboard` with browser-based Chart.js visualizations

All three interfaces consume the same IndexStats dataclass and display consistent data.

**For Phase 36 (Developer Skills):**
- Stats commands can be documented in skill routing guidance
- Dashboard URLs can be referenced in developer workflows
- /api/stats endpoint provides programmatic access for external tools

**For Phase 37 (Documentation Rebrand):**
- serve-dashboard command showcases observability features
- Web dashboard demonstrates polish and professional UX
- Three-interface approach (CLI/terminal/web) shows thoughtful design

No blockers. All verification criteria met, bugs fixed, dashboard production-ready.

---
*Phase: 35-stats-dashboard*
*Completed: 2026-02-05*
