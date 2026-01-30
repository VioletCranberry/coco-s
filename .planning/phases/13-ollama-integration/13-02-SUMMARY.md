---
phase: 13-ollama-integration
plan: 02
subsystem: testing
tags: [ollama, integration-tests, embeddings, pytest, cosine-similarity]

# Dependency graph
requires:
  - phase: 13-ollama-integration
    plan: 01
    provides: Ollama fixtures with native detection and session-scoped warmup
provides:
  - Ollama integration tests validating embedding dimensions, values, and semantic similarity
  - Cosine similarity helper for vector comparison
  - Test coverage for real embedding generation behavior
affects: [14-e2e-flows]

# Tech tracking
tech-stack:
  added: []
  patterns: [cosine-similarity vector comparison, batch embedding flow pattern]

key-files:
  created:
    - tests/integration/test_ollama.py
  modified: []

key-decisions:
  - "6 tests split into 2 classes: TestEmbeddingGeneration (basic properties) and TestEmbeddingSimilarity (semantic behavior)"
  - "Similarity thresholds: > 0.8 for similar texts, < 0.7 for dissimilar texts, > 0.5 for code vs description"
  - "Batch embedding pattern: Generate multiple embeddings in single flow call for efficiency"
  - "Cosine similarity helper function at module level for reuse across tests"

patterns-established:
  - "Pattern 1: Batch embedding generation using cocoindex.DataSlice([text1, text2]) for efficiency"
  - "Pattern 2: Cosine similarity calculation via np.dot(a,b) / (np.linalg.norm(a) * np.linalg.norm(b))"
  - "Pattern 3: Test structure follows test_postgresql.py patterns (class-based organization, requirement comments)"

# Metrics
duration: 111s
completed: 2026-01-30
---

# Phase 13 Plan 02: Ollama Integration Tests Summary

**Integration tests validating real Ollama embedding generation with dimension checks, value validation, and semantic similarity scoring**

## Performance

- **Duration:** 1m 51s
- **Started:** 2026-01-30T13:24:18Z
- **Completed:** 2026-01-30T13:26:09Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments
- 6 comprehensive integration tests validating real embedding generation
- TestEmbeddingGeneration class tests fundamental properties: 768 dimensions, valid float values, deterministic output
- TestEmbeddingSimilarity class tests semantic understanding: similar texts (> 0.8), dissimilar texts (< 0.7), code vs description (> 0.5)
- Tests skip gracefully when Ollama unavailable with clear setup instructions
- Batch embedding pattern for efficiency

## Task Commits

Each task was committed atomically:

1. **Task 1: Create embedding dimension and value validation tests** - `917d23a` (test)
2. **Task 2: Create similarity sanity tests** - `8c11fdf` (test)

## Files Created/Modified
- `tests/integration/test_ollama.py` - New integration test module with 6 tests across 2 classes

## Decisions Made

**1. Test structure and organization**
- Split into 2 classes: TestEmbeddingGeneration for basic properties, TestEmbeddingSimilarity for semantic behavior
- Follows test_postgresql.py patterns for consistency
- Requirement comments link tests to OLLAMA-01 and OLLAMA-03 requirements

**2. Similarity thresholds for semantic validation**
- Similar texts (sorting descriptions): > 0.8 cosine similarity
- Dissimilar texts (sorting vs cake recipe): < 0.7 cosine similarity
- Code vs natural language: > 0.5 (related but not identical)
- These thresholds validate that nomic-embed-text understands semantic meaning

**3. Batch embedding pattern for efficiency**
- Use `cocoindex.DataSlice([text1, text2])` to generate multiple embeddings in single flow call
- Avoids repeated flow construction overhead
- More realistic pattern for production usage

**4. Cosine similarity helper function**
- Module-level function for reuse across test classes
- Standard implementation: np.dot / (norm_a * norm_b)
- Returns float in [-1, 1] range

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Tests skip gracefully when Ollama unavailable (either native or Docker). Error messages provide clear setup instructions.

## User Setup Required

None for test infrastructure. Tests will skip if Ollama unavailable.

For running tests with real embeddings:
1. Install Ollama: https://ollama.ai/download
2. Pull model: `ollama pull nomic-embed-text`
3. Start service: `ollama serve`

Or ensure Docker is available for container fallback.

## Next Phase Readiness

Ready for Phase 14 (E2E Flows). Integration test infrastructure complete:
- Unit tests (Phase 11)
- PostgreSQL integration tests (Phase 12)
- Ollama integration tests (Phase 13)

No blockers. Can now build end-to-end flows that combine:
- Real code parsing (existing)
- Real embeddings (Ollama - Phase 13)
- Real vector storage (PostgreSQL+pgvector - Phase 12)

---
*Phase: 13-ollama-integration*
*Completed: 2026-01-30*
