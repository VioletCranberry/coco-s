# Phase 33: Deferred v1.7 Foundation - Research

**Researched:** 2026-02-03
**Domain:** Query caching, hybrid search filtering, symbol hierarchy
**Confidence:** HIGH

## Summary

Phase 33 completes deferred features from v1.7 milestone, addressing three distinct technical domains: (1) combining hybrid search with symbol filters (currently falls back to vector-only), (2) enriching symbol names with parent context for disambiguation, and (3) implementing query-level caching for repeated and semantically similar queries.

The research reveals established patterns for each domain. Query caching should use hash-based exact matching combined with embedding similarity for semantic cache hits. Hybrid search filtering requires applying filters before RRF fusion rather than after. Symbol hierarchy is already partially implemented (ClassName.method_name format exists) but needs consistent display in output.

**Primary recommendation:** Use diskcache for persistent query caching with 24-hour TTL, apply symbol filters to both vector and keyword search before RRF fusion, and enhance formatter to consistently display qualified symbol names.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| diskcache | 5.6.1 | Persistent query cache | Thread-safe, process-safe, SQLite-backed, widely adopted for LLM/ML caching |
| hashlib | stdlib | Query hash generation | Standard library, SHA256 for cache keys |
| psycopg[pool] | 3.3.2+ | Database connections | Already used, connection pool for efficiency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| functools.lru_cache | stdlib | In-memory metadata cache | Already used for symbol column checks (db.py:18) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| diskcache | Redis/Memcached | External dependency, network overhead, overkill for single-machine semantic search |
| diskcache | functools.lru_cache | In-memory only, doesn't persist across restarts, inappropriate for query cache |
| Hash-based | Query string only | Whitespace/formatting differences break cache, parameter-order dependent |

**Installation:**
```bash
# No new dependencies required
# diskcache available if needed: pip install diskcache
```

## Architecture Patterns

### Recommended Project Structure
```
src/cocosearch/search/
├── query.py              # Main search entry point (add cache layer)
├── cache.py              # NEW: Query cache module
├── hybrid.py             # Extend with filter support
├── filters.py            # Existing symbol filter SQL builder
└── formatter.py          # Enhance for qualified symbol names
```

### Pattern 1: Two-Level Query Caching

**What:** Combine exact match (hash-based) and semantic similarity (embedding-based) caching
**When to use:** For embedding-heavy operations where query variations are common

**Example:**
```python
# Source: Medium article on hash-caching query results
# Adapted for semantic search with embedding similarity

import hashlib
from diskcache import Cache

cache = Cache('.cache/queries', size_limit=1e9)  # 1GB limit

def cache_search_results(query: str, index_name: str, **params):
    # Level 1: Exact match via hash
    cache_key = hashlib.sha256(
        f"{query}|{index_name}|{params}".encode()
    ).hexdigest()

    if cache_key in cache:
        return cache[cache_key]

    # Level 2: Semantic similarity check
    query_embedding = code_to_embedding.eval(query)
    for cached_query, cached_data in cache.items():
        if cached_data.get('embedding') is not None:
            similarity = cosine_similarity(
                query_embedding,
                cached_data['embedding']
            )
            if similarity > 0.95:  # Threshold from research
                return cached_data['results']

    # Cache miss: execute search
    results = execute_search(query, index_name, **params)

    cache.set(
        cache_key,
        {'results': results, 'embedding': query_embedding},
        expire=86400  # 24 hours
    )
    return results
```

### Pattern 2: Pre-Fusion Filtering for Hybrid Search

**What:** Apply filters to vector and keyword result sets before RRF fusion
**When to use:** When combining multiple search strategies with metadata filters

**Example:**
```python
# Source: OpenSearch RRF documentation + Azure Hybrid Search docs
# Pattern: Filter → Search → Fuse (not Search → Fuse → Filter)

def hybrid_search_with_filters(
    query: str,
    index_name: str,
    symbol_type: str = None,
    symbol_name: str = None
):
    # Build WHERE clause for both searches
    where_clause, params = build_symbol_where_clause(
        symbol_type, symbol_name
    )

    # Execute vector search WITH filter
    vector_results = execute_vector_search(
        query, table_name, limit,
        where_clause=where_clause,
        where_params=params
    )

    # Execute keyword search WITH filter
    keyword_results = execute_keyword_search(
        query, table_name, limit,
        where_clause=where_clause,
        where_params=params
    )

    # Fuse filtered results
    return rrf_fusion(vector_results, keyword_results)
```

### Pattern 3: Qualified Symbol Names in Output

**What:** Display symbols with parent context (ClassName.method_name) in all output formats
**When to use:** When symbol names alone are ambiguous (multiple init methods, get functions)

**Example:**
```python
# Already implemented in symbols.py extraction
# Need consistent display in formatter.py

def format_symbol_info(result: SearchResult) -> str:
    if result.symbol_name:
        # symbol_name already includes parent: "UserService.get_user"
        return f"[{result.symbol_type}] {result.symbol_name}"
    return ""
```

### Anti-Patterns to Avoid

- **Post-fusion filtering:** Applying symbol filters after RRF fusion breaks rank-based scoring semantics and filters out results that should contribute to fusion
- **Query string-only cache keys:** Whitespace/case differences cause cache misses; must normalize or use structured parameters
- **Unbounded cache growth:** Set size limits (e.g., 1GB) and use LRU eviction to prevent disk exhaustion
- **Cache stampede:** When popular cache entry expires, add jitter to TTLs (e.g., 24h ± 1h) to stagger expirations

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Persistent cache | Custom file-based cache with locks | diskcache | Thread-safe, process-safe, handles eviction, backed by SQLite |
| Cache invalidation | Manual deletion or timestamp tracking | diskcache TTL + reindex hook | TTL handles staleness, invalidate on reindex via callback |
| Embedding similarity | Manual dot product calculation | Existing PostgreSQL cosine operator | Already optimized, pgvector handles it |
| Query normalization | Custom string cleaning | Parameter-based hashing | Order-independent, type-safe, explicit |

**Key insight:** Caching for database-backed search has unique challenges (query parameter handling, embedding comparison, invalidation on reindex). Existing solutions like diskcache handle persistence and concurrency better than custom implementations, while semantic similarity requires threshold tuning that's well-documented in LLM caching literature.

## Common Pitfalls

### Pitfall 1: Cache Key Collisions with Query Parameters

**What goes wrong:** Using query string only as cache key causes misses when parameters differ (limit, filters, index_name)
**Why it happens:** Natural language queries look similar but parameters change behavior
**How to avoid:** Include all parameters in cache key: `hash(query + index_name + str(sorted(params.items())))`
**Warning signs:** Cache hit rate lower than expected, same query text giving different results

### Pitfall 2: Symbol Filter Breaking Hybrid Search

**What goes wrong:** Current code (query.py:269) detects symbol filters and falls back to vector-only search
**Why it happens:** Filters not implemented for hybrid path, only for vector-only path
**How to avoid:** Pass filter WHERE clause to both execute_vector_search and execute_keyword_search
**Warning signs:** `--hybrid --symbol-type function` returns only semantic results, missing keyword matches

### Pitfall 3: Cache Invalidation Not Atomic with Reindex

**What goes wrong:** Reindex completes but cache still serves stale results from old index
**Why it happens:** No hook to clear cache when indexing starts/finishes
**How to avoid:** Add cache.clear() call in indexing flow or use index version in cache key
**Warning signs:** New code indexed but search returns old results until TTL expires

### Pitfall 4: Semantic Cache Threshold Too Low

**What goes wrong:** Cosine similarity 0.8 causes false positives (different queries sharing tokens)
**Why it happens:** Semantic embeddings cluster similar topics, not just paraphrases
**How to avoid:** Use 0.95 threshold (from research) or make it configurable; log cache hits for tuning
**Warning signs:** Search results don't match query intent, debugging shows semantic cache hit

### Pitfall 5: Symbol Hierarchy Not Displayed Consistently

**What goes wrong:** Symbol extraction stores qualified names but formatter shows raw names
**Why it happens:** Formatter extracts symbol from result but doesn't use qualified name field
**How to avoid:** Always use symbol_name field (already contains "Class.method"), don't parse signature
**Warning signs:** Multiple results show same function name without class context

## Code Examples

Verified patterns from codebase and official sources:

### Embedding Cosine Similarity Check
```python
# Source: CocoSearch src/cocosearch/indexer/embedder.py
# Pattern: Reuse existing embedding function for cache similarity

from cocosearch.indexer.embedder import code_to_embedding

def compute_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    """Compute cosine similarity between two embeddings.

    Returns value in [0, 1] where 1 is identical, 0 is orthogonal.
    """
    # Using PostgreSQL's formula from hybrid.py:229
    # score = 1 - (embedding <=> query_embedding)
    # where <=> is cosine distance operator

    import numpy as np
    e1 = np.array(embedding1)
    e2 = np.array(embedding2)

    # Cosine similarity = dot product / (norm1 * norm2)
    cos_sim = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
    return float(cos_sim)
```

### Symbol Filter SQL Extension
```python
# Source: CocoSearch src/cocosearch/search/filters.py
# Pattern: Reuse existing filter builder, extend for hybrid context

def execute_vector_search(
    query: str,
    table_name: str,
    limit: int = 10,
    where_clause: str = "",
    where_params: list = None,
) -> list[VectorResult]:
    """Execute vector search with optional WHERE clause."""
    pool = get_connection_pool()
    query_embedding = code_to_embedding.eval(query)

    # Add WHERE clause if provided
    where_sql = f"WHERE {where_clause}" if where_clause else ""

    sql = f"""
        SELECT
            filename,
            lower(location) as start_byte,
            upper(location) as end_byte,
            1 - (embedding <=> %s::vector) AS score,
            block_type,
            hierarchy,
            language_id
        FROM {table_name}
        {where_sql}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    # Build params: embedding + where_params + embedding + limit
    params = [query_embedding]
    if where_params:
        params.extend(where_params)
    params.extend([query_embedding, limit])

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [VectorResult(...) for row in rows]
```

### Cache Invalidation Hook
```python
# Source: Diskcache documentation + CocoSearch indexing flow
# Pattern: Clear cache when indexing starts

from diskcache import Cache
from cocosearch.search.cache import get_query_cache

def run_index(index_name: str, path: str, config: IndexingConfig):
    """Main indexing function with cache invalidation."""

    # Invalidate query cache before indexing
    cache = get_query_cache()
    cache_prefix = f"{index_name}:"

    # Clear all cached queries for this index
    for key in list(cache.iterkeys()):
        if key.startswith(cache_prefix):
            cache.delete(key)

    # Proceed with indexing
    # ... existing indexing logic ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| In-memory query cache | Persistent disk cache | 2024+ LLM apps | Cache survives restarts, reduces cold-start latency |
| Single threshold similarity | Dynamic or ensemble thresholds | 2025 research | Better precision/recall tradeoff, reduces false positives |
| Post-filtering in RRF | Pre-filtering before fusion | OpenSearch 2.19 (Nov 2025) | Preserves ranking semantics, improves relevance |
| Fixed TTL | TTL with jitter | Netflix 2022 | Prevents cache stampede, reduces DB load spikes |
| Manual cache keys | Structured hashing | Standard practice | Eliminates collisions, parameter-order independent |

**Deprecated/outdated:**
- **functools.lru_cache for query results**: In-memory only, doesn't persist; appropriate for metadata/config but not for expensive search results
- **Redis for single-machine caching**: Network overhead unnecessary when search and cache on same host; diskcache matches Redis performance for local use

## Open Questions

1. **Semantic cache threshold tuning**
   - What we know: Research suggests 0.95 for FAQ-style caching, 0.88 for general semantic similarity
   - What's unclear: Optimal threshold for code search queries (may differ from natural language)
   - Recommendation: Start with 0.95, make configurable via environment variable, log cache hits for analysis

2. **Cache size limits**
   - What we know: Diskcache supports size_limit parameter, LRU eviction
   - What's unclear: Reasonable default for code search (depends on query patterns, index size)
   - Recommendation: Set 1GB default (stores ~10K-100K cached queries depending on result size), document tuning

3. **Cache warming strategy**
   - What we know: Cold cache causes latency spikes on first queries
   - What's unclear: Whether to pre-warm with common queries or let it build organically
   - Recommendation: Start without warming (simpler), consider later if cold-start issues emerge

4. **Hybrid search filter performance**
   - What we know: Filters work in vector-only mode, need to work before RRF
   - What's unclear: Whether filtering 2x result sets (vector + keyword) significantly impacts performance
   - Recommendation: Implement and measure; filtering is indexed (symbol columns, WHERE clause), should be fast

## Sources

### Primary (HIGH confidence)

- [Diskcache documentation](https://grantjenks.com/docs/diskcache/) - Persistent caching API and best practices
- [Medium: Hash-Caching query results in Python](https://medium.com/gousto-engineering-techbrunch/hash-caching-query-results-in-python-2d00f8058252) - Hash-based cache key generation
- [Redis Blog: 10 techniques for semantic cache optimization](https://redis.io/blog/10-techniques-for-semantic-cache-optimization/) - Cosine similarity thresholds (0.95 recommendation)
- [Brain.co: Semantic Caching](https://brain.co/blog/semantic-caching-accelerating-beyond-basic-rag) - Embedding reuse patterns, similarity thresholds
- [OpenSearch: Introducing RRF for hybrid search](https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/) - RRF with filtering best practices
- [Daily.dev: Cache invalidation vs expiration](https://daily.dev/blog/cache-invalidation-vs-expiration-best-practices) - TTL strategies and hybrid approaches
- [OneUpTime: Cache invalidation strategies](https://oneuptime.com/blog/post/2026-01-30-cache-invalidation-strategies/view) - Event-driven and TTL patterns (Jan 2026)

### Secondary (MEDIUM confidence)

- [Python Discuss: Caching SQL queries](https://discuss.python.org/t/how-to-cache-data-from-sql-queries/61534) - Community patterns for query caching
- [PostgreSQL caching overview](https://severalnines.com/blog/overview-caching-postgresql/) - Database-level caching patterns
- [Elastic: RRF ranking](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) - RRF documentation with filtering
- [Azure: Hybrid search ranking](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) - RRF scoring patterns

### Tertiary (LOW confidence)

- [Arxiv: Ensemble embedding for semantic caching](https://arxiv.org/html/2507.07061v1) - Research on threshold tuning (2025), not production-tested
- [Talk Python podcast: Diskcache episode](https://talkpython.fm/episodes/show/534/diskcache-your-secret-python-perf-weapon) - Library overview, less technical depth

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - diskcache widely adopted, documented, stable; no new external dependencies for basic hash caching
- Architecture: HIGH - Existing codebase patterns well-established (filters.py, hybrid.py), extension points clear
- Pitfalls: HIGH - Research reveals well-known issues (cache stampede, threshold tuning, post-fusion filtering problems)
- Performance: MEDIUM - Cache overhead and filter impact need measurement in real codebases

**Research date:** 2026-02-03
**Valid until:** 60 days (stable domain, diskcache mature, RRF patterns established)
