# Quick Task 001: Update test_flow.py Tests for Handler Architecture

**Task:** Update the 3 failing tests in tests/unit/indexer/test_flow.py to reflect the new handler architecture from Phase 21

## Background

Phase 21 refactored language handlers to use a registry pattern. Three tests in test_flow.py still checked for the old architecture:

1. Old: `DEVOPS_CUSTOM_LANGUAGES` constant
   New: `get_custom_languages()` function from handlers

2. Old: `extract_devops_metadata` returns `DevOpsMetadata` dataclass
   New: Returns dict with metadata fields

3. Old: Import from `cocosearch.indexer.metadata`
   New: Import from `cocosearch.handlers`

## Tasks

- [x] Task 1: Update `test_flow_module_imports_custom_languages` to check for `get_custom_languages`
- [x] Task 2: Update `test_extract_devops_metadata_is_cocoindex_op` to expect dict return
- [x] Task 3: Update `test_flow_source_has_metadata_import` to check handlers import

## Success Criteria

- [ ] All 20 tests in test_flow.py pass
- [ ] No regressions in other unit tests
