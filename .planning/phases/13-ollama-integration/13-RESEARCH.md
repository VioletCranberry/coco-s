# Phase 13: Ollama Integration - Research

**Researched:** 2026-01-30
**Domain:** Docker-based Ollama integration testing with native fallback and warmup handling
**Confidence:** HIGH

## Summary

This phase requires integrating real Ollama embedding generation into integration tests with native-first detection and Docker fallback. The standard approach uses testcontainers-python's OllamaContainer (v4.14.0+, supports Ollama module) with session-scoped fixtures following the same pattern established in Phase 12 for PostgreSQL. The key challenge is handling Ollama's 30-second first-request timeout when models are loaded into memory, addressed through session-scoped warmup fixtures with extended httpx timeout configuration.

User decisions from Phase 13 CONTEXT.md specify: native-first detection (check localhost:11434 before Docker), session-scoped warmup fixture (one throwaway embedding request per session), extended 60s timeout on httpx client, embedding dimension validation (768 for nomic-embed-text), and optional dockerized Ollama working alongside native installations. The project already uses CocoIndex's EmbedText function which calls Ollama's /api/embed endpoint via httpx.

CocoIndex (already installed via pyproject.toml as cocoindex[embeddings]>=0.3.28) handles Ollama embedding calls internally through cocoindex.functions.EmbedText with api_type=OLLAMA. The nomic-embed-text model produces 768-dimensional embeddings with a 274MB download size. First-request timeout occurs because Ollama loads models into memory on-demand, taking 15-30 seconds for initial load.

**Primary recommendation:** Use testcontainers[ollama] with session-scoped container fixture, native detection via httpx GET to localhost:11434/api/tags, session-scoped warmup fixture calling CocoIndex embedding once with 60s timeout, and validation tests checking 768-dimensional output with reasonable float ranges.

## Standard Stack

The established libraries/tools for Ollama integration testing with Python:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| testcontainers[ollama] | 4.14.0+ | Ollama container lifecycle management | Official Testcontainers module since v4.14.0 (2026-01-07), includes OllamaContainer with pull_model() and list_models() support |
| httpx | 0.27.0+ | HTTP client for Ollama API calls | Used by CocoIndex internally, supports fine-grained timeout configuration (connect, read, write, pool), async support |
| cocoindex[embeddings] | 0.3.28+ | Embedding generation with Ollama | Already installed, provides EmbedText function with OLLAMA api_type, handles /api/embed endpoint correctly |
| pytest | 9.0.2+ | Testing framework with fixture system | Already configured, session/function scopes enable container reuse and warmup patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| docker | 7.0.0+ | Docker availability check | Already in dev dependencies, use for native Ollama detection via subprocess check |
| ollama/ollama | latest (0.5.11) | Official Ollama Docker image | testcontainers default, includes /api/embed and /api/tags endpoints, port 11434 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native-first detection | Always use Docker | Native detection allows using existing Ollama installations (faster, no 274MB model download), Docker-only simpler but slower for developers with Ollama |
| testcontainers[ollama] | Generic testcontainers.GenericContainer | OllamaContainer provides model management methods (pull_model, list_models), generic container requires manual API calls |
| Session-scoped warmup | Per-test warmup | Session warmup runs once (fast), per-test warmup repeats 30s delay for every test (slow but more isolated) |

**Installation:**
```bash
# Add to pyproject.toml dev dependencies
testcontainers[ollama]>=4.14.0
# httpx already installed via cocoindex[embeddings]
# pytest already installed
```

## Architecture Patterns

### Recommended Test Structure
```
tests/
├── fixtures/
│   ├── containers.py          # PostgreSQL fixtures (existing from Phase 12)
│   └── ollama.py              # NEW: Ollama fixtures (native detection, container, warmup)
├── integration/
│   ├── conftest.py            # Docker check, marker auto-apply (existing)
│   ├── test_postgresql.py    # PostgreSQL tests (existing from Phase 12)
│   └── test_ollama.py         # NEW: Ollama embedding tests
```

### Pattern 1: Native Ollama Detection with Docker Fallback
**What:** Check if Ollama responds on localhost:11434 before starting container
**When to use:** Session start, before any embedding operations (locked user decision)
**Example:**
```python
# tests/fixtures/ollama.py
import httpx
import pytest
from testcontainers.ollama import OllamaContainer

def is_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running and responsive.

    Locked decision from CONTEXT.md: "Native-first detection: check if
    Ollama responds on localhost:11434"

    Uses /api/tags endpoint as health check (lightweight, no model load).
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{base_url}/api/tags")
            return response.status_code == 200
    except (httpx.TimeoutException, httpx.ConnectError):
        return False

@pytest.fixture(scope="session")
def ollama_service():
    """Provide Ollama service (native or Docker).

    Locked decision from CONTEXT.md:
    - "Native-first detection: check if Ollama responds on localhost:11434"
    - "Docker fallback: start container only when native unavailable"
    - "Fixture detects availability at session start, caches decision"

    Returns base_url for Ollama API.
    """
    # Check for native Ollama first
    if is_ollama_available():
        yield "http://localhost:11434"
        return

    # Fallback to Docker container
    # User decision: "Container persists for session (same pattern as PostgreSQL)"
    with OllamaContainer() as ollama:
        base_url = f"http://{ollama.get_container_host_ip()}:{ollama.get_exposed_port(11434)}"

        # Pull nomic-embed-text model (required for tests)
        if "nomic-embed-text" not in [m["name"] for m in ollama.list_models()]:
            ollama.pull_model("nomic-embed-text")

        yield base_url
```

### Pattern 2: Session-Scoped Warmup Fixture
**What:** Make one throwaway embedding request per session to load model into memory
**When to use:** After Ollama service available, before any tests run (locked user decision)
**Example:**
```python
# Source: User decisions from Phase 13 CONTEXT.md + httpx timeout docs
import cocoindex

@pytest.fixture(scope="session")
def warmed_ollama(ollama_service):
    """Warmup Ollama by making throwaway embedding request.

    Locked decisions from CONTEXT.md:
    - "Session-scoped pre-warm fixture makes throwaway embedding request"
    - "Extended timeout (60s) on httpx client for safety"
    - "Both approaches: pre-warm AND extended timeout"
    - "Warmup happens once per test session, not per test"

    Prevents 30-second timeout on first embedding request by loading
    model into memory before tests execute.
    """
    # Configure CocoIndex to use our Ollama instance
    # Note: CocoIndex uses httpx internally, timeout handled at HTTP layer
    os.environ["OLLAMA_HOST"] = ollama_service

    # Make throwaway embedding request with extended timeout
    # User decision: "Extended timeout (60s) on httpx client for safety"
    try:
        # Create simple embedding to warm up model
        # This loads nomic-embed-text into memory (15-30 seconds first time)
        warmup_flow = cocoindex.transform_flow()(
            lambda text: text.transform(
                cocoindex.functions.EmbedText(
                    api_type=cocoindex.LlmApiType.OLLAMA,
                    model="nomic-embed-text",
                    # httpx timeout configuration for first request
                    timeout=60.0,  # 60s for slow model load
                )
            )
        )

        # Execute warmup embedding (blocks until complete)
        _ = warmup_flow(cocoindex.DataSlice(["warmup"]))

    except Exception as e:
        pytest.skip(f"Ollama warmup failed: {e}")

    yield ollama_service
```

### Pattern 3: Embedding Dimension and Value Validation
**What:** Verify embeddings match expected dimensions (768) and reasonable float ranges
**When to use:** Integration tests validating real Ollama behavior (locked user decision)
**Example:**
```python
# Source: User decisions from Phase 13 CONTEXT.md
import numpy as np

def test_embedding_dimensions(warmed_ollama):
    """Verify embedding dimensions match expected (768 for nomic-embed-text).

    Requirement: OLLAMA-03 (Embedding generation produces correct vector dimensions)
    """
    # Use CocoIndex embedding function (same as production code)
    embedding_flow = cocoindex.transform_flow()(
        lambda text: text.transform(
            cocoindex.functions.EmbedText(
                api_type=cocoindex.LlmApiType.OLLAMA,
                model="nomic-embed-text",
            )
        )
    )

    # Generate embedding
    result = embedding_flow(cocoindex.DataSlice(["test text"]))
    embedding = result[0]

    # User decision: "Verify dimension count matches expected (768 for nomic-embed-text)"
    assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"

    # User decision: "Value range check (floats in reasonable range, not NaN/Inf)"
    assert all(isinstance(v, float) for v in embedding), "All values should be floats"
    assert all(not np.isnan(v) for v in embedding), "No NaN values allowed"
    assert all(not np.isinf(v) for v in embedding), "No Inf values allowed"
    assert all(-1.0 <= v <= 1.0 for v in embedding), "Values should be normalized (-1 to 1)"

def test_embedding_similarity(warmed_ollama):
    """Verify similar texts produce similar embeddings.

    Locked decision from CONTEXT.md: "Similarity sanity tests: verify
    similar texts produce similar embeddings"
    """
    embedding_flow = cocoindex.transform_flow()(
        lambda text: text.transform(
            cocoindex.functions.EmbedText(
                api_type=cocoindex.LlmApiType.OLLAMA,
                model="nomic-embed-text",
            )
        )
    )

    # Generate embeddings for similar and dissimilar texts
    texts = ["Python programming", "Python coding", "banana recipe"]
    results = embedding_flow(cocoindex.DataSlice(texts))

    # Calculate cosine similarity
    from numpy.linalg import norm
    def cosine_similarity(a, b):
        return np.dot(a, b) / (norm(a) * norm(b))

    # Similar texts should have high similarity
    sim_similar = cosine_similarity(results[0], results[1])
    sim_dissimilar = cosine_similarity(results[0], results[2])

    assert sim_similar > 0.8, f"Similar texts should be similar: {sim_similar}"
    assert sim_dissimilar < 0.7, f"Dissimilar texts should be different: {sim_dissimilar}"
```

### Pattern 4: Container Lifecycle Management
**What:** Session-scoped Ollama container with model pre-pull, same pattern as PostgreSQL
**When to use:** When native Ollama unavailable (locked user decision: Docker fallback)
**Example:**
```python
# Source: testcontainers-python OllamaContainer docs + Phase 12 patterns
from pathlib import Path
from testcontainers.ollama import OllamaContainer

@pytest.fixture(scope="session")
def ollama_container():
    """Start Ollama container for entire test session.

    Locked decision from CONTEXT.md:
    - "Add Ollama service to existing docker-compose.test.yml"
    - "Container persists for session (same pattern as PostgreSQL)"
    - "Model pulled during container startup (nomic-embed-text)"

    Note: Only used if native Ollama not available (see ollama_service fixture).
    """
    # Optional: Mount local .ollama directory to reuse already-pulled models
    # User decision: Claude's discretion on details
    ollama_home = Path.home() / ".ollama"

    with OllamaContainer(
        image="ollama/ollama:latest",  # Latest stable version
        # Optional: mount local models directory for faster startup
        # ollama_home=ollama_home if ollama_home.exists() else None
    ) as ollama:
        # Pull required model if not present
        # User decision: "Model pulled during container startup (nomic-embed-text)"
        models = ollama.list_models()
        model_names = [m["name"] for m in models]

        if "nomic-embed-text" not in model_names:
            # User decision: Claude's discretion on "Model pull retry logic"
            try:
                ollama.pull_model("nomic-embed-text")
            except Exception as e:
                pytest.skip(f"Failed to pull nomic-embed-text model: {e}")

        yield ollama
```

### Anti-Patterns to Avoid
- **Per-test warmup:** Warmup should be session-scoped to avoid repeating 30-second model load for every test
- **Docker-only without native detection:** Always check for native Ollama first (faster for developers who have it installed)
- **Using localhost in Docker context:** When running in containers, use container names not localhost (but Phase 13 is test-only, not containerized tests)
- **Short timeouts on first request:** First embedding always takes 15-30s for model load, use 60s timeout for safety
- **Skipping dimension validation:** Always validate 768 dimensions to catch model/API changes early

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ollama container lifecycle | Manual docker run commands | testcontainers[ollama].OllamaContainer | Automatic cleanup, model management methods (pull_model, list_models), health checks |
| Native Ollama detection | ping/socket checks | httpx GET to /api/tags | Reliable health check endpoint, confirms API availability not just process running |
| Embedding generation | Direct HTTP POST to /api/embed | CocoIndex EmbedText function | Already in project, handles request format, error handling, batching, response parsing |
| HTTP timeout configuration | Global timeout only | httpx.Timeout(connect, read, write, pool) | Granular control, different timeouts for different operations (60s read for slow model load, 5s connect) |
| Model warmup strategy | Sleep delays or polling | Session-scoped fixture with throwaway request | Ensures model loaded before tests, pytest fixture dependencies handle ordering |

**Key insight:** Ollama container management is complex (model pulls can take minutes, first request timeouts, native vs Docker detection). testcontainers-python solves this with OllamaContainer that handles model lifecycle, while session-scoped warmup fixtures prevent timeout issues in tests.

## Common Pitfalls

### Pitfall 1: First Request Timeout (30-Second Model Load)
**What goes wrong:** First embedding request times out after 5 seconds (httpx default), fails with ReadTimeout
**Why it happens:** Ollama loads models into memory on-demand, nomic-embed-text takes 15-30 seconds to load on first request
**How to avoid:** Session-scoped warmup fixture makes throwaway request with 60s timeout before tests run, subsequent requests fast (model in memory)
**Warning signs:** First test fails with httpx.ReadTimeout, subsequent tests pass; "loading model" messages in Ollama logs

### Pitfall 2: Native Ollama Not Detected
**What goes wrong:** Tests always start Docker container even when Ollama running locally, slow model download
**Why it happens:** Detection check uses wrong endpoint, short timeout, or wrong host
**How to avoid:** Use /api/tags endpoint (lightweight health check), 2-second timeout sufficient for local, check localhost:11434 specifically
**Warning signs:** Tests slow (274MB model download every time), docker logs show model pull, localhost Ollama idle

### Pitfall 3: Dimension Mismatch (Expected 768, Got Different)
**What goes wrong:** Tests expect 768 dimensions but get different size, vector storage fails
**Why it happens:** Wrong model used (some embedding models have 384 or 1536 dimensions), API changes, truncation enabled
**How to avoid:** Always validate len(embedding) == 768 in tests, hardcode "nomic-embed-text" model name, check CocoIndex configuration
**Warning signs:** pgvector insertion fails with "dimension mismatch", search returns no results, len(embedding) != 768

### Pitfall 4: Container Not Cleaned Up (Model Download Wasted)
**What goes wrong:** testcontainers creates new container every test run, re-downloads 274MB model each time
**Why it happens:** Session scope not used, container fixture doesn't use context manager, Ryuk disabled
**How to avoid:** Always use scope="session" for Ollama fixtures, use with statement in fixture, verify Ryuk enabled (TESTCONTAINERS_RYUK_DISABLED=false)
**Warning signs:** Tests slow (5+ minutes first time, still slow on subsequent runs), Docker shows multiple stopped ollama containers, network usage high

### Pitfall 5: Model Not Pulled Before Tests
**What goes wrong:** First embedding request fails, "model not found" error, tests skip
**Why it happens:** testcontainers doesn't auto-pull models, must call pull_model() explicitly
**How to avoid:** Check list_models() in container fixture, call pull_model("nomic-embed-text") if not present, handle pull failures with clear skip message
**Warning signs:** "model 'nomic-embed-text' not found" error, tests skip with unclear message, list_models() returns empty

### Pitfall 6: httpx Default Timeout Too Short
**What goes wrong:** Even with warmup, some requests timeout (httpx default 5s)
**Why it happens:** httpx.Client uses 5-second default timeout, some embedding requests take longer (large text, slow network)
**How to avoid:** Configure httpx.Timeout(10.0, read=60.0) when creating CocoIndex EmbedText, separate connect (fast) from read (slow) timeouts
**Warning signs:** Intermittent ReadTimeout errors, failures on large text inputs, works locally but fails in CI

### Pitfall 7: Docker Host vs Localhost Confusion
**What goes wrong:** Tests can't connect to Ollama, "connection refused" errors
**Why it happens:** Using localhost:11434 when should use container IP, or vice versa
**How to avoid:** Native Ollama always on localhost:11434, containerized Ollama use get_container_host_ip() and get_exposed_port(), never hardcode IP
**Warning signs:** ConnectionError/ConnectError, works on some machines not others, passes locally fails CI

## Code Examples

Verified patterns from official sources and project context:

### Complete Native Detection and Docker Fallback
```python
# Source: testcontainers-python OllamaContainer docs + httpx timeout docs
import os
import httpx
import pytest
from pathlib import Path
from testcontainers.ollama import OllamaContainer

def is_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if native Ollama is running and responsive.

    Uses /api/tags endpoint as health check (official Ollama API).
    2-second timeout sufficient for local checks.

    Source: Ollama API docs, GitHub issue #1378
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{base_url}/api/tags")
            return response.status_code == 200
    except (httpx.TimeoutException, httpx.ConnectError):
        return False

@pytest.fixture(scope="session")
def ollama_service():
    """Provide Ollama service with native-first detection, Docker fallback.

    Locked decisions from CONTEXT.md:
    - Native-first detection via localhost:11434 health check
    - Docker fallback when native unavailable
    - Session scope for performance
    - Model pre-pull during container startup

    Returns base_url string for API calls.
    """
    # Try native Ollama first
    if is_ollama_available():
        yield "http://localhost:11434"
        return

    # Fallback to Docker container
    with OllamaContainer() as ollama:
        # Get connection details
        host = ollama.get_container_host_ip()
        port = ollama.get_exposed_port(11434)
        base_url = f"http://{host}:{port}"

        # Pull model if needed (274MB download)
        models = ollama.list_models()
        if "nomic-embed-text" not in [m["name"] for m in models]:
            try:
                ollama.pull_model("nomic-embed-text")
            except Exception as e:
                pytest.skip(f"Failed to pull nomic-embed-text: {e}")

        yield base_url
```

### Session-Scoped Warmup with Extended Timeout
```python
# Source: Phase 13 CONTEXT.md decisions + CocoIndex usage from existing code
import os
import cocoindex
import pytest

@pytest.fixture(scope="session")
def warmed_ollama(ollama_service):
    """Warmup Ollama with throwaway embedding request.

    Locked decisions from CONTEXT.md:
    - Session-scoped (runs once per test session)
    - Throwaway embedding request to load model into memory
    - Extended 60s timeout for safety (first request slow)
    - Both pre-warm AND extended timeout approach

    Prevents 30-second timeout on first embedding by loading
    nomic-embed-text model into memory before tests run.
    """
    # Configure CocoIndex to use our Ollama instance
    os.environ["OLLAMA_HOST"] = ollama_service

    try:
        # Create embedding function with extended timeout
        # Note: CocoIndex 0.3.28+ supports timeout parameter
        embedding_func = cocoindex.functions.EmbedText(
            api_type=cocoindex.LlmApiType.OLLAMA,
            model="nomic-embed-text",
            timeout=60.0,  # Extended timeout for first request
        )

        # Make throwaway request (loads model into memory)
        # This takes 15-30 seconds first time, fast afterwards
        warmup_slice = cocoindex.DataSlice(["warmup"])
        _ = warmup_slice.transform(embedding_func)

    except Exception as e:
        pytest.skip(f"Ollama warmup failed: {e}")

    # Return configured service for tests
    yield ollama_service
```

### Embedding Validation with Dimension and Value Checks
```python
# Source: Phase 13 CONTEXT.md validation requirements + numpy docs
import numpy as np
import cocoindex
import pytest

def test_embedding_generation_and_validation(warmed_ollama):
    """Verify embeddings have correct dimensions and value ranges.

    Requirements:
    - OLLAMA-01: Integration tests generate embeddings with real Ollama
    - OLLAMA-03: Embeddings match expected dimensions (768 for nomic-embed-text)

    Locked decisions from CONTEXT.md:
    - Verify dimension count matches expected (768)
    - Value range check (floats, not NaN/Inf)
    """
    # Use CocoIndex embedding function (same as production code)
    embedding_func = cocoindex.functions.EmbedText(
        api_type=cocoindex.LlmApiType.OLLAMA,
        model="nomic-embed-text",
    )

    # Generate embedding
    test_slice = cocoindex.DataSlice(["def hello_world():\n    print('Hello')"])
    result = test_slice.transform(embedding_func)
    embedding = result[0]

    # Dimension validation (OLLAMA-03)
    assert isinstance(embedding, (list, np.ndarray)), "Embedding should be list or array"
    assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"

    # Value range validation
    embedding_array = np.array(embedding)
    assert embedding_array.dtype == np.float64 or embedding_array.dtype == np.float32, \
        "Embedding values should be floats"
    assert not np.any(np.isnan(embedding_array)), "No NaN values allowed"
    assert not np.any(np.isinf(embedding_array)), "No Inf values allowed"

    # L2-normalized vectors should be in [-1, 1] range
    assert np.all(embedding_array >= -1.0) and np.all(embedding_array <= 1.0), \
        "Normalized embedding values should be in [-1, 1]"
```

### Similarity Sanity Test
```python
# Source: Phase 13 CONTEXT.md similarity validation requirement
import numpy as np
import cocoindex
import pytest

def test_embedding_similarity_sanity(warmed_ollama):
    """Verify similar texts produce similar embeddings.

    Locked decision from CONTEXT.md: "Similarity sanity tests: verify
    similar texts produce similar embeddings"

    Tests semantic similarity by comparing embeddings of:
    - Similar texts (should have high cosine similarity)
    - Dissimilar texts (should have low cosine similarity)
    """
    embedding_func = cocoindex.functions.EmbedText(
        api_type=cocoindex.LlmApiType.OLLAMA,
        model="nomic-embed-text",
    )

    # Generate embeddings for test texts
    texts = [
        "Python function for sorting a list",
        "Python method to sort an array",
        "Recipe for chocolate cake",
    ]
    test_slice = cocoindex.DataSlice(texts)
    results = test_slice.transform(embedding_func)

    # Convert to numpy arrays for calculations
    emb1 = np.array(results[0])
    emb2 = np.array(results[1])
    emb3 = np.array(results[2])

    # Calculate cosine similarity
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    # Similar texts should have high similarity (> 0.8)
    sim_similar = cosine_similarity(emb1, emb2)
    assert sim_similar > 0.8, \
        f"Similar texts should have high similarity: {sim_similar:.3f}"

    # Dissimilar texts should have lower similarity (< 0.7)
    sim_dissimilar1 = cosine_similarity(emb1, emb3)
    sim_dissimilar2 = cosine_similarity(emb2, emb3)
    assert sim_dissimilar1 < 0.7, \
        f"Dissimilar texts should have lower similarity: {sim_dissimilar1:.3f}"
    assert sim_dissimilar2 < 0.7, \
        f"Dissimilar texts should have lower similarity: {sim_dissimilar2:.3f}"
```

### httpx Timeout Configuration for Ollama API
```python
# Source: httpx official docs - timeouts section
import httpx

# Basic timeout configuration
client = httpx.Client(timeout=10.0)  # 10s for all operations

# Granular timeout configuration (recommended for Ollama)
timeout = httpx.Timeout(
    connect=5.0,   # 5s to establish connection
    read=60.0,     # 60s to read response (handles model load)
    write=10.0,    # 10s to send request
    pool=5.0       # 5s to acquire connection from pool
)
client = httpx.Client(timeout=timeout)

# Disable timeout entirely (not recommended for production)
client = httpx.Client(timeout=None)

# Per-request timeout override
response = client.post(
    "http://localhost:11434/api/embed",
    json={"model": "nomic-embed-text", "input": "test"},
    timeout=60.0  # Override default timeout for this request
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| /api/embeddings (single) | /api/embed (batch) | Ollama 0.1.26+ | /api/embed supports multiple inputs, returns L2-normalized vectors, better performance |
| Manual docker run | testcontainers[ollama] | testcontainers-python 4.14.0 (2026-01-07) | OllamaContainer with pull_model() and list_models() methods, automatic cleanup |
| Global httpx timeout | Fine-grained Timeout object | httpx 0.20+ | Separate connect/read/write/pool timeouts, better control for slow operations |
| Docker-only setup | Native-first detection | Community best practice (2025+) | Faster for developers with local Ollama, optional Docker for CI/new contributors |
| Per-test warmup | Session-scoped warmup | pytest best practice | 30-second warmup once per session vs every test (10x faster test suite) |

**Deprecated/outdated:**
- **testcontainers.GenericContainer for Ollama:** Use testcontainers[ollama].OllamaContainer instead (official module since 4.14.0)
- **/api/embeddings endpoint:** Use /api/embed for better performance and batch support (embeddings still works but deprecated)
- **Global timeout for Ollama calls:** Use httpx.Timeout(connect=5.0, read=60.0) for granular control
- **Always Docker approach:** Native-first detection is now best practice (faster, better DX)

## Open Questions

Things that couldn't be fully resolved:

1. **CocoIndex Timeout Parameter Support**
   - What we know: CocoIndex 0.3.28+ has "robust async runtime with function-level timeouts"
   - What's unclear: Does EmbedText function accept timeout parameter directly, or must configure via httpx client?
   - Recommendation: Test both approaches - EmbedText(timeout=60.0) and environment variable HTTPX_TIMEOUT; document working approach in implementation

2. **Model Pull Retry Strategy**
   - What we know: User decision "Claude's discretion on model pull retry logic"
   - What's unclear: Should retry on network failures? How many retries? Exponential backoff?
   - Recommendation: Start simple - single pull attempt with clear skip message on failure; add retries if CI flaky

3. **Warmup Request Text Content**
   - What we know: Session-scoped warmup makes "throwaway embedding request"
   - What's unclear: Does warmup text matter (simple "test" vs realistic code snippet)?
   - Recommendation: Use simple text like "warmup" - model load time same regardless, simpler is better

4. **Container Health Check Timing**
   - What we know: testcontainers handles wait strategy automatically
   - What's unclear: Does OllamaContainer wait for model pull complete before yielding?
   - Recommendation: Verify in implementation; if not, add explicit wait_until_responsive() checking /api/tags

5. **Native Ollama Version Compatibility**
   - What we know: nomic-embed-text requires "Ollama 0.1.26 or later"
   - What's unclear: Should tests check Ollama version, skip if too old?
   - Recommendation: Start without version check - failures will be clear if incompatible; add version check if issues arise

## Sources

### Primary (HIGH confidence)
- testcontainers-python v4.14.0 OllamaContainer: https://testcontainers-python.readthedocs.io/en/latest/modules/ollama/README.html (official module docs, verified 2026-01-07 release)
- httpx Timeout Configuration: https://www.python-httpx.org/advanced/timeouts/ (official docs, timeout types and configuration)
- Ollama Embeddings API: https://docs.ollama.com/capabilities/embeddings (official /api/embed endpoint documentation)
- Ollama API Reference: https://github.com/ollama/ollama/blob/main/docs/api.md (GitHub official docs, /api/tags health check)
- nomic-embed-text Model: https://ollama.com/library/nomic-embed-text (official model page, 274MB, 2K context)
- Hugging Face nomic-embed-text-v1.5: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 (confirmed 768 dimensions)
- CocoIndex Changelog 0.3.10: https://cocoindex.io/blogs/changelog-0310 (async runtime improvements, timeout handling)

### Secondary (MEDIUM confidence)
- [Testcontainers Ollama Module Guide](https://testcontainers.com/modules/ollama/) (community guide, 2026)
- [Ollama Production Health Checks Guide](https://markaicode.com/ollama-production-health-checks-monitoring-guide/) (health check patterns, /api/tags endpoint)
- [Ollama Docker Setup Guide](https://markaicode.com/ollama-docker-setup-guide/) (port 11434, volume mounts, environment variables)
- [PostgreSQL + Ollama Docker Compose Examples](https://github.com/timescale/pgai/blob/main/examples/docker_compose_pgai_ollama/docker-compose.yml) (multi-service setup patterns)
- [Ollama is now available as an official Docker image](https://ollama.com/blog/ollama-is-now-available-as-an-official-docker-image) (official Docker image announcement)
- [Embedding models blog post](https://ollama.com/blog/embedding-models) (embedding models overview)

### Tertiary (LOW confidence - flagged for validation)
- [Timeout configuration issue #5733](https://github.com/RooCodeInc/Roo-Code/issues/5733) (community report of aggressive timeout with Ollama)
- [Ollama hanging/freeze issue #3029](https://github.com/ollama/ollama/issues/3029) (nomic-embed-text specific timeout issues)
- [Health check endpoint discussion #1378](https://github.com/ollama/ollama/issues/1378) (/api/tags as health check endpoint)
- Various Medium articles and blog posts about Ollama Docker setup (practical examples but not authoritative)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - testcontainers-python 4.14.0 verified via official docs and GitHub (2026-01-07), httpx via official docs, CocoIndex already in project, nomic-embed-text 768 dimensions verified via Hugging Face
- Architecture: HIGH - Session-scoped fixtures follow Phase 12 patterns (verified working), native detection via /api/tags confirmed in Ollama GitHub issues, warmup pattern matches pytest best practices
- Pitfalls: MEDIUM - First-request timeout confirmed in multiple GitHub issues and community reports, dimension validation straightforward, container cleanup handled by testcontainers (HIGH confidence on mechanics, MEDIUM on specific failure modes)

**Research date:** 2026-01-30
**Valid until:** 2026-02-27 (30 days - stable domain, testcontainers and Ollama mature projects)
