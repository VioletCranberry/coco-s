# Phase 18: Dogfooding Validation - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

CocoSearch repository uses CocoSearch with documented example. Create cocosearch.yaml config and README section that lets new contributors search the codebase with CocoSearch.

</domain>

<decisions>
## Implementation Decisions

### Config content
- Index name: `self` (meta — indexing itself)
- File types: Python, DevOps (Dockerfile, docker-compose, bash), and Markdown
- Include test files (tests/unit/, tests/integration/) — useful for finding test patterns
- Rely on CocoSearch's default exclude patterns (no explicit __pycache__, .git, .venv)
- Keep config minimal — demonstrates defaults work well

### README structure
- Section header: "Searching CocoSearch" (descriptive, clear)
- Placement: After Quick Start section
- Depth: Brief demo (3-4 example commands)
- Standalone commands — doesn't assume user ran dev-setup.sh
- Link to dev-setup.sh for full environment setup

### Example queries
- Mix of implementation and architecture questions
- CLI commands only (not REPL)
- Include annotated output showing what was found
- At least one example with --lang flag for filtering

### Contributor flow
- Prerequisites: Docker + Python 3.12+ with uv installed
- Include verification step: `cocosearch info self` after indexing
- Cross-reference dev-setup.sh for full development environment

### Claude's Discretion
- Number of example queries (balance breadth vs brevity)
- Whether to include timing estimate for indexing
- Specific example queries that demonstrate value
- Output truncation style in annotations

</decisions>

<specifics>
## Specific Ideas

- User suggested table of contents for README — noted but out of scope for this phase
- Index name "self" chosen for its meta quality

</specifics>

<deferred>
## Deferred Ideas

- README table of contents — consider for future documentation improvement phase

</deferred>

---

*Phase: 18-dogfooding-validation*
*Context gathered: 2026-01-31*
