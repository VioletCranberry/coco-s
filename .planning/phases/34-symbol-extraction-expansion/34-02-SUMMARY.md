---
phase: 34
plan: 02
subsystem: indexing
tags: [symbol-extraction, java, ruby, tree-sitter, query-files]

dependencies:
  requires: [34-01]
  provides: [java-symbol-extraction, ruby-symbol-extraction]
  affects: [34-03]

tech-stack:
  added: []
  patterns: [query-based-extraction-per-language]

files:
  created:
    - src/cocosearch/indexer/queries/java.scm
    - src/cocosearch/indexer/queries/ruby.scm
  modified:
    - src/cocosearch/indexer/symbols.py
    - tests/unit/indexer/test_symbols.py

decisions:
  - context: Two-pass extraction processing
    decision: Process all definitions first, then all names
    rationale: Ensures all definition nodes are registered before matching names to prevent incorrect parent assignment
    commit: 18eea1f (as part of 34-03)

metrics:
  duration: 9m 27s
  completed: 2026-02-03
---

# Phase 34 Plan 02: Java and Ruby Symbol Extraction Summary

> Add Java and Ruby symbol extraction using external query files.

**One-liner:** Java and Ruby symbol extraction with qualified names for methods (MyClass.method).

## What Was Built

### Query Files

**Java (`java.scm`):**
- Classes, interfaces, enums
- Methods and constructors
- All mapped to appropriate symbol types

**Ruby (`ruby.scm`):**
- Classes and modules
- Instance methods (`def method`)
- Singleton methods (`def self.method`)

### Language Support

**Java extensions:** `.java`
**Ruby extensions:** `.rb`

Both added to `LANGUAGE_MAP` with appropriate container types for qualified name building.

### Container Types Configuration

**Java:** `class_declaration`, `interface_declaration`, `enum_declaration`
**Ruby:** `class`, `module`

These enable qualified names like:
- Java: `UserService.getName`, `Repository.save`
- Ruby: `User.greet`, `Authentication.validate`

## Tests

**TestJavaSymbols:** 6 test cases
- Simple class, interface, enum extraction
- Method in class (first symbol check)
- Constructor extraction
- Empty input handling

**TestRubySymbols:** 5 test cases
- Simple class and module extraction
- Instance and singleton method extraction
- Empty input handling

All tests pass.

## Deviations from Plan

### Work Already Completed

**Context:** Plan 34-02 was to add Java and Ruby symbol extraction with dedicated commits per task. However, when executing this plan, all implementation work had already been completed in prior commits:

**Task 1 (Java extraction):**
- `java.scm` created and committed in: b6d2c28 (34-03 test commit)
- LANGUAGE_MAP updated in: 18eea1f (34-03 C++ commit)
- Container types added in: 18eea1f (34-03 C++ commit)

**Task 2 (Ruby extraction):**
- `ruby.scm` created and committed in: b6d2c28 (34-03 test commit)
- LANGUAGE_MAP updated in: 18eea1f (34-03 C++ commit)
- Container types added in: 18eea1f (34-03 C++ commit)

**Task 3 (Tests):**
- Java and Ruby tests added and committed in: aa07d05 (34-04 commit)

**Root cause:** Plans were executed out of order (34-03 and 34-04 before 34-02), and Java/Ruby support was bundled into those commits.

**Action taken:** Verified all functionality works correctly, confirmed tests pass, and documented the situation in this summary. No new commits made since all work is already done.

**Deviation rule:** This is a unique situation not explicitly covered by deviation rules - work was completed but not in the expected task-by-task commits. Treated as a "pre-completed plan" scenario.

### Bug Fix During Verification

**Issue:** When testing Java interface extraction, discovered that method names inside interfaces were overwriting the interface name itself (e.g., "Repository" was replaced with "save").

**Root cause:** The `_extract_symbols_with_query` function processed captures in dictionary iteration order, which meant "definition.interface" was processed, then "name", then "definition.method". When "save" name was processed, the method_declaration wasn't in the definitions dict yet, so "save" walked up the tree to interface_declaration and overwrote the interface's name.

**Fix:** Modified extraction to use two-pass processing:
1. First pass: Register all definitions
2. Second pass: Match names to definitions

This ensures all definition nodes exist before name matching begins.

**Commit:** 18eea1f (as part of 34-03 C++ commit)

**Status:** Already committed in prior plan execution. This was a critical correctness fix required for interface and nested class extraction to work properly.

## Key Links Established

**From `symbols.py` to `LANGUAGE_MAP`:**
- `"java": "java"` enables Java file recognition
- `"rb": "ruby"` enables Ruby file recognition

**From query files to symbol database:**
- Java classes/interfaces/enums → `symbol_type: class/interface`
- Ruby classes/modules → `symbol_type: class`
- Java/Ruby methods → `symbol_type: method` with qualified names

## Verification Results

### Manual Testing

**Java:**
```java
class UserService {
    public String getName() {
        return name;
    }
}
```
→ Extracts: `UserService` (class), `UserService.getName` (method)

**Ruby:**
```ruby
class User
  def greet
    "Hello"
  end
end
```
→ Extracts: `User` (class), `User.greet` (method)

### Test Suite

All 11 tests pass:
- 6 Java symbol tests
- 5 Ruby symbol tests

### Must-Haves Verification

✓ Java files have classes, interfaces, enums, methods extracted as symbols
✓ Ruby files have classes, modules, methods extracted as symbols
✓ Java method names include parent class (MyClass.myMethod)
✓ Ruby method names include parent class/module (MyClass.my_method)

## Commits

**No new commits** - All work completed in prior commits:
- b6d2c28: Created java.scm and ruby.scm query files (as part of 34-03 tests)
- 18eea1f: Updated symbols.py with Java/Ruby support (as part of 34-03 C++)
- aa07d05: Added Java and Ruby tests (as part of 34-04)
- a4fb28d: Fixed test API usage (bug fix for query-based extraction)

## Next Phase Readiness

**Blockers:** None

**For 34-03 (C/C++):** Already completed

**For future phases:** Java and Ruby symbol extraction is production-ready and tested.

## Research & Future Improvements

**Qualified name patterns observed:**
- Java uses dot separator: `UserService.getName`
- Ruby uses dot separator: `User.greet`
- Singleton methods work correctly: `User.find` for `def self.find`

**Potential enhancements:**
- Add support for Java inner classes (nested class extraction)
- Add support for Ruby namespaced classes (Module::Class)
- Consider extracting Java annotations as metadata
- Consider extracting Ruby method visibility (private, protected, public)
