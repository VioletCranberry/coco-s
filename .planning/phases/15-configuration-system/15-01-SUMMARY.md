# Phase 15 Plan 01: Configuration Schema & Loader Summary

**One-liner:** Pydantic-based YAML config schema with strict validation, file discovery in cwd/git-root, and comprehensive error handling

---

## Metadata

```yaml
phase: 15-configuration-system
plan: 01
subsystem: configuration
status: complete
type: execute
completed: 2026-01-31
duration: 3 minutes

requires:
  - PyYAML library (already in dependencies)
  - Pydantic (via cocoindex dependency)

provides:
  - CocoSearchConfig schema with nested sections
  - Config file discovery (cwd and git root)
  - YAML loading with validation
  - ConfigError exception for all config errors

affects:
  - 15-02 (will use config schema for error formatting)
  - 16-01 (CLI will integrate load_config)
  - 17-01 (dev setup will use config for initialization)

tags: [configuration, pydantic, yaml, validation, schema]

tech-stack:
  added:
    - pydantic: "Strict schema validation with extra='forbid'"
    - yaml: "Safe YAML parsing with error reporting"
  patterns:
    - "Nested configuration sections (indexing, search, embedding)"
    - "camelCase naming convention for config keys"
    - "Config file discovery: cwd → git-root fallback"
    - "Defaults-first: missing config returns valid defaults"

key-files:
  created:
    - src/cocosearch/config/__init__.py: "Public exports for config module"
    - src/cocosearch/config/schema.py: "Pydantic models with strict validation"
    - src/cocosearch/config/loader.py: "File discovery and YAML loading"
    - tests/unit/config/test_schema.py: "21 schema validation tests"
    - tests/unit/config/test_loader.py: "15 loader and discovery tests"
  modified: []

decisions:
  - id: CONF-SCHEMA-STRUCTURE
    choice: "Nested sections (indexing, search, embedding) vs flat keys"
    rationale: "Logical grouping improves readability and maintainability"
  - id: CONF-NAMING-CONVENTION
    choice: "camelCase for all config keys"
    rationale: "Aligns with CONTEXT.md decision for consistency"
  - id: CONF-VALIDATION-STRATEGY
    choice: "Strict validation (extra='forbid', strict=True)"
    rationale: "Catch typos and config errors early, per CONTEXT.md"
  - id: CONF-DISCOVERY-ORDER
    choice: "cwd/cocosearch.yaml → git-root/cocosearch.yaml → defaults"
    rationale: "Local config overrides repo config, graceful fallback"
  - id: CONF-ERROR-HANDLING
    choice: "ConfigError for all errors with line/column for YAML"
    rationale: "User-friendly error messages, detailed context"
```

---

## What Was Built

Created the foundational configuration system for CocoSearch with Pydantic schema validation and YAML file loading.

### Configuration Schema (schema.py)

**ConfigError Exception:**
- Custom exception class for all configuration-related errors
- Used for YAML parsing errors and validation failures

**IndexingSection:**
- `includePatterns: list[str]` - File patterns to include (default: empty)
- `excludePatterns: list[str]` - File patterns to exclude (default: empty)
- `languages: list[str]` - Languages to index (default: empty = all)
- `chunkSize: int` - Chunk size in bytes (default: 1000, must be > 0)
- `chunkOverlap: int` - Chunk overlap in bytes (default: 300, must be >= 0)

**SearchSection:**
- `resultLimit: int` - Maximum search results (default: 10, must be > 0)
- `minScore: float` - Minimum relevance score (default: 0.3, range: 0.0-1.0)

**EmbeddingSection:**
- `model: str` - Embedding model name (default: "nomic-embed-text")

**CocoSearchConfig (root):**
- `indexName: str | None` - Optional index name override (default: None)
- `indexing: IndexingSection` - Indexing configuration
- `search: SearchSection` - Search configuration
- `embedding: EmbeddingSection` - Embedding configuration

All models use `extra='forbid'` and `strict=True` for strict validation.

### Configuration Loader (loader.py)

**find_config_file() -> Path | None:**
- Searches for `cocosearch.yaml` in current directory first
- Falls back to git root if not found in cwd
- Returns None if no config file exists (graceful degradation)
- Handles git errors gracefully (not in a git repo)

**load_config(path: Path | None = None) -> CocoSearchConfig:**
- Accepts optional explicit path parameter
- Auto-discovers config file if path is None
- Returns defaults when no config file found (no error)
- Parses YAML with `yaml.safe_load()`
- Handles empty YAML files (returns defaults)
- Validates with Pydantic and raises ConfigError on validation errors
- Extracts line/column information for YAML syntax errors
- Re-raises validation errors as ConfigError for consistent error handling

### Public API (__init__.py)

Exports:
- `CocoSearchConfig` - Root config model
- `IndexingSection`, `SearchSection`, `EmbeddingSection` - Section models
- `ConfigError` - Configuration exception
- `load_config` - Primary loading function
- `find_config_file` - File discovery function

---

## Implementation Details

### Task Breakdown

**Task 1: Config schema (5dfd3d8)**
- Created `src/cocosearch/config/` module
- Implemented all Pydantic models with strict validation
- Added ConfigError exception class
- Created loader.py with file discovery and YAML loading
- All models use camelCase field names per CONTEXT.md

**Task 2: Config loader**
- Completed in Task 1 (loader.py created together with schema)
- File discovery implemented with cwd → git-root fallback
- YAML loading with comprehensive error handling

**Task 3: Unit tests (5d0c69f)**
- Created `tests/unit/config/` directory
- 21 schema validation tests (test_schema.py)
- 15 loader tests (test_loader.py)
- Coverage: defaults, validation, constraints, error handling, file discovery
- All 36 tests passing

### Key Design Decisions

**Strict Validation:**
- Used `extra='forbid'` to reject unknown fields immediately
- Used `strict=True` to prevent type coercion (e.g., "10" rejected for int field)
- This catches typos and misconfigurations early per CONTEXT.md requirements

**Error Handling:**
- All errors raised as ConfigError for consistent handling
- YAML syntax errors include line/column information from yaml.YAMLError
- Validation errors wrapped with context (formatting improved in Plan 02)
- File read errors caught and wrapped with helpful messages

**Graceful Defaults:**
- Missing config file returns valid defaults (no error)
- Empty YAML file returns defaults
- YAML with only comments returns defaults
- This aligns with "mention on first run" requirement from CONTEXT.md

**File Discovery:**
- cwd takes precedence over git root (local overrides repo)
- Git errors handled gracefully (subprocess.CalledProcessError)
- Returns None when no config found (caller decides defaults)

---

## Testing

**Test Coverage: 36 tests, all passing**

### Schema Tests (21 tests)

**IndexingSection (6 tests):**
- Default values
- Valid config with all fields
- Unknown field rejection
- Strict type validation
- chunkSize > 0 constraint
- chunkOverlap >= 0 constraint

**SearchSection (5 tests):**
- Default values
- Valid config
- Unknown field rejection
- resultLimit > 0 constraint
- minScore 0.0-1.0 range constraint

**EmbeddingSection (3 tests):**
- Default values
- Valid config
- Unknown field rejection

**CocoSearchConfig (7 tests):**
- Default values for all sections
- Valid config with all fields
- Partial config (some sections)
- Unknown field rejection at root
- Unknown field rejection in nested sections
- model_dump serialization

### Loader Tests (15 tests)

**find_config_file (5 tests):**
- Returns None when no config exists
- Finds config in cwd
- Finds config in git root
- Prefers cwd over git root
- Handles git errors gracefully

**load_config (10 tests):**
- Returns defaults when no config file
- Parses valid YAML
- Handles empty YAML file
- Handles YAML with only comments
- Raises ConfigError on invalid YAML syntax (with line/column)
- Raises ConfigError on validation errors
- Raises ConfigError on unknown field
- Raises ConfigError on type mismatch
- Loads partial config
- Accepts explicit path parameter
- Raises ConfigError on file read error

---

## Verification Results

All verification criteria passed:

1. **Import check:** All exports available from `cocosearch.config`
2. **Test suite:** 36/36 tests passing
3. **Unknown field rejection:** Pydantic ValidationError raised correctly
4. **Missing config handling:** Returns defaults without error

### Example Usage

```python
from cocosearch.config import load_config, ConfigError

# Load config (auto-discovers cocosearch.yaml)
try:
    config = load_config()
    print(f"Index name: {config.indexName}")
    print(f"Chunk size: {config.indexing.chunkSize}")
    print(f"Result limit: {config.search.resultLimit}")
except ConfigError as e:
    print(f"Config error: {e}")

# Default values when no config file
config = load_config()  # No error, returns defaults
assert config.indexing.chunkSize == 1000
assert config.search.resultLimit == 10
```

---

## Deviations from Plan

None - plan executed exactly as written.

All required fields (CONF-02 through CONF-07) are present in schema:
- CONF-02: indexName (root level)
- CONF-03: indexing.includePatterns, excludePatterns, languages
- CONF-04: indexing.chunkSize, chunkOverlap
- CONF-05: search.resultLimit, minScore
- CONF-06: embedding.model
- CONF-07: All fields have documented defaults

---

## Decisions Made

| ID | Decision | Impact |
|----|----------|--------|
| CONF-SCHEMA-STRUCTURE | Nested sections (indexing, search, embedding) | Better organization, clear grouping |
| CONF-NAMING-CONVENTION | camelCase for all config keys | Consistency with CONTEXT.md |
| CONF-VALIDATION-STRATEGY | Strict validation (extra='forbid', strict=True) | Early error detection, no silent failures |
| CONF-DISCOVERY-ORDER | cwd → git-root → defaults | Local config overrides repo config |
| CONF-ERROR-HANDLING | ConfigError with line/column for YAML | User-friendly error messages |

---

## Next Phase Readiness

**Ready for 15-02:** Error formatting and typo suggestions

This plan provides:
- ConfigError exception ready for enhanced formatting
- Validation errors from Pydantic (need formatting in Plan 02)
- Schema field names for typo suggestion (difflib.get_close_matches)

**Ready for 16-01:** CLI integration

This plan provides:
- `load_config()` function ready for CLI use
- CocoSearchConfig model for merging with CLI flags
- ConfigError for CLI error handling

**Blockers:** None

**Concerns:** None

---

## Commits

| Hash | Message | Files |
|------|---------|-------|
| 5dfd3d8 | feat(15-01): create config schema with Pydantic models | schema.py, loader.py, __init__.py |
| 5d0c69f | test(15-01): add comprehensive unit tests for config module | test_schema.py, test_loader.py |

**Total commits:** 2 (schema + tests)
**Lines added:** ~620 (156 implementation + 464 tests)

---

*Completed: 2026-01-31*
*Duration: 3 minutes*
*Status: All tasks complete, all tests passing*
