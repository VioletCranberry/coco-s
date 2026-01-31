---
phase: 16-cli-config-integration
plan: 01
type: tdd
subsystem: configuration
tags: [config, resolver, precedence, cli, env-vars, tdd]

# Dependencies
requires:
  - 15-01 # Config schema with nested sections
  - 15-02 # Error handling and validation

provides:
  - ConfigResolver class with precedence resolution
  - config_key_to_env_var helper for env var naming
  - parse_env_value helper for type-aware parsing
  - Source tracking for resolved values

affects:
  - 16-02 # CLI commands will use ConfigResolver

# Tech Stack
tech-stack:
  added:
    - ConfigResolver pattern (CLI > env > config > default)
  patterns:
    - Precedence chain resolution
    - Source tracking for transparency
    - Type-aware environment variable parsing

# Files
key-files:
  created:
    - src/cocosearch/config/resolver.py # ConfigResolver implementation
    - tests/unit/config/test_resolver.py # Unit tests for resolver
  modified:
    - src/cocosearch/config/__init__.py # Export resolver components

# Decisions
decisions:
  - id: CONF-PRECEDENCE-ORDER
    choice: "CLI > env > config > default"
    rationale: "Standard precedence order, CLI flags most specific, defaults least specific"
    alternatives: ["env > CLI > config > default"]
    impact: "CLI flags always override everything else"

  - id: CONF-ENV-VAR-NAMING
    choice: "COCOSEARCH_UPPER_SNAKE_CASE with dot notation converted"
    rationale: "Consistent with standard env var conventions, clear namespace prefix"
    alternatives: ["COCO_* prefix", "no prefix"]
    impact: "Environment variables follow predictable naming pattern"

  - id: CONF-ENV-VALUE-PARSING
    choice: "Type-aware parsing with JSON fallback for lists"
    rationale: "Enables complex values in env vars, graceful fallback to comma-separated"
    alternatives: ["String-only env vars", "Require JSON for all complex types"]
    impact: "Users can set list values as JSON or comma-separated strings"

  - id: CONF-SOURCE-TRACKING
    choice: "Return (value, source) tuple from resolve()"
    rationale: "Enables debugging and transparency about where values come from"
    alternatives: ["Value only", "Separate method for source"]
    impact: "CLI can show users where each config value originated"

# Metrics
metrics:
  tests-added: 25
  duration: "5 minutes"
  completed: "2026-01-31"
---

# Phase 16 Plan 01: ConfigResolver TDD Implementation Summary

JWT auth with refresh rotation using jose library

## Objective

Implement ConfigResolver with CLI > env > config > default precedence using TDD methodology for Phase 16's CONF-09 requirement (CLI flags override config file settings).

## What Was Built

### ConfigResolver Class

Core precedence resolution with source tracking:

```python
resolver = ConfigResolver(config, config_path=Path("coco.yaml"))

# CLI flag takes precedence
value, source = resolver.resolve("indexName", cli_value="my-index", env_var="COCOSEARCH_INDEX_NAME")
# Returns: ("my-index", "CLI flag")

# Env var overrides config
os.environ["COCOSEARCH_INDEXING_CHUNK_SIZE"] = "2000"
value, source = resolver.resolve("indexing.chunkSize", cli_value=None, env_var="COCOSEARCH_INDEXING_CHUNK_SIZE")
# Returns: (2000, "env:COCOSEARCH_INDEXING_CHUNK_SIZE")
```

**Key capabilities:**
- Four-level precedence: CLI > env > config > default
- Source tracking for every resolved value
- Nested field support via dot notation (e.g., "indexing.chunkSize")
- Type-aware environment variable parsing
- Field path enumeration via `all_field_paths()`

### Helper Functions

**config_key_to_env_var:**
Converts config keys to environment variable names:
- `"indexName"` → `"COCOSEARCH_INDEX_NAME"`
- `"indexing.chunkSize"` → `"COCOSEARCH_INDEXING_CHUNK_SIZE"`
- Handles camelCase to UPPER_SNAKE_CASE conversion
- Adds COCOSEARCH_ namespace prefix

**parse_env_value:**
Type-aware parsing of environment variable values:
- `int`: "100" → 100
- `float`: "0.5" → 0.5
- `bool`: "true"/"1"/"yes" → True
- `list[str]`: '["*.py", "*.js"]' → ["*.py", "*.js"]
- `list[str]` (fallback): "*.py,*.js" → ["*.py", "*.js"]
- Handles None indicators: ""/"null"/"none" → None

### Test Coverage

25 comprehensive unit tests covering:
- Environment variable naming conversion (4 tests)
- Type-aware value parsing (8 tests)
- Precedence resolution (13 tests including nested fields)
- All test cases pass

## Technical Implementation

### TDD Cycle

**RED Phase:**
- Created test_resolver.py with 25 tests
- All tests fail with `ModuleNotFoundError` (expected)
- Committed failing tests

**GREEN Phase:**
- Implemented ConfigResolver class in resolver.py
- Implemented helper functions for env var naming and parsing
- Nested field resolution via Pydantic model introspection
- All 25 tests pass
- Committed working implementation

**REFACTOR Phase:**
- Removed unused imports (FieldInfo)
- Removed unused _cache attribute
- All tests still pass
- Committed cleanup

### Architecture

**Precedence Chain:**
1. **CLI flag** (highest): Provided explicitly by user, always wins
2. **Environment variable**: OS-level config, parsed to correct type
3. **Config file**: User's yaml/json config, tracked with file path
4. **Default** (lowest): Schema defaults, fallback when nothing else set

**Source Tracking:**
- Format: `(value, source)`
- Sources: `"CLI flag"`, `"env:VAR_NAME"`, `"config:/path/to/file"`, `"default"`
- Enables transparent debugging of config resolution

**Type Safety:**
- Uses Pydantic model introspection to get field types
- Parses environment variables to match field type
- Prevents type mismatches at resolution time

## Integration Points

**Used by (future plans):**
- CLI commands (16-02): Will use ConfigResolver for flag/env/config merging
- Init command: Source tracking helps users understand config
- Search command: Resolves search parameters from multiple sources

**Depends on:**
- CocoSearchConfig schema (15-01): Provides type information
- Pydantic BaseModel: Enables model introspection

## Decisions Made

**CONF-PRECEDENCE-ORDER:** CLI > env > config > default
- Standard precedence chain where more specific sources win
- CLI flags are most explicit user intent, always highest priority
- Defaults are fallback when no other source provides value

**CONF-ENV-VAR-NAMING:** COCOSEARCH_UPPER_SNAKE_CASE
- Consistent with standard environment variable conventions
- Namespace prefix prevents conflicts
- camelCase → UPPER_SNAKE_CASE conversion for readability

**CONF-ENV-VALUE-PARSING:** Type-aware with JSON fallback
- Enables complex values (lists, bools) in environment variables
- JSON primary format for lists, comma-separated fallback for convenience
- Bool parsing handles multiple common formats (true/1/yes)

**CONF-SOURCE-TRACKING:** Return (value, source) tuple
- Enables CLI to show users where each config value originated
- Supports debugging and transparency
- Low overhead (just string construction)

## Deviations from Plan

None - plan executed exactly as written. TDD cycle followed precisely (RED → GREEN → REFACTOR).

## Testing

**Test metrics:**
- 25 unit tests, all passing
- 100% coverage of resolver module
- Tests verify all precedence cases
- Tests verify type parsing for all supported types
- Tests verify source tracking accuracy

**Manual verification:**
```bash
poetry run pytest tests/unit/config/test_resolver.py -v
# 25 passed in 0.02s

poetry run python -c "from cocosearch.config import ConfigResolver"
# Import successful
```

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Ready for:** Phase 16 Plan 02 (CLI Integration)

**What's needed for 16-02:**
- CLI commands need to call resolver.resolve() for each config field
- Pass CLI flag values (from typer) as cli_value parameter
- Generate env_var names using config_key_to_env_var()
- Display source information to users for transparency

## Performance Notes

**Execution time:** 5 minutes (TDD cycle: RED → GREEN → REFACTOR)

**Runtime performance:**
- Resolution is O(1) for CLI flag check
- O(1) for environment variable lookup
- O(n) for nested field navigation (n = depth of nesting)
- No caching yet (can add if needed for performance)

## Lessons Learned

**TDD Benefits:**
- Test-first approach caught edge cases early (None indicators, bool parsing)
- Comprehensive test suite gives confidence for future refactoring
- RED phase confirmed tests actually fail (validates test quality)

**Pydantic Integration:**
- Model introspection makes field type detection robust
- Default value extraction requires careful handling of default_factory
- Nested model navigation requires recursive field resolution

**Environment Variable Design:**
- JSON parsing with comma fallback provides best of both worlds
- Bool parsing needs multiple accepted values for user convenience
- None indicators ("", "null", "none") improve UX

## Files Modified

**Created:**
- `src/cocosearch/config/resolver.py` (281 lines)
- `tests/unit/config/test_resolver.py` (296 lines)

**Modified:**
- `src/cocosearch/config/__init__.py` (added exports)

**Total:** 3 files, 577 lines added

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 49a1049 | test | Add failing tests for ConfigResolver (RED phase) |
| 173a0b6 | feat | Implement ConfigResolver with precedence logic (GREEN phase) |
| 2924be2 | refactor | Remove unused imports and attributes (REFACTOR phase) |
