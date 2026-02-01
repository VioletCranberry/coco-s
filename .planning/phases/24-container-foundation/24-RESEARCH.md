# Phase 24: Container Foundation - Research

**Researched:** 2026-02-01
**Domain:** Docker multi-service containers with s6-overlay process supervision
**Confidence:** HIGH

## Summary

This phase involves creating an all-in-one Docker container that bundles PostgreSQL, Ollama, and the MCP server under s6-overlay process supervision. The research covers s6-overlay v3 service management (the chosen process supervisor per CONTEXT.md), PostgreSQL signal handling for graceful shutdown, Ollama model preloading patterns, and Docker healthcheck best practices.

The key challenge is coordinating three services with dependencies: PostgreSQL must be accepting connections before the MCP server starts, and Ollama must have the embedding model loaded for fast first-request response. s6-overlay v3's s6-rc service manager handles this through explicit dependency declarations and readiness notification.

**Primary recommendation:** Use s6-overlay v3.2.2.0 with s6-rc service definitions, PostgreSQL with SIGINT stop signal for fast shutdown, and the gerke74/ollama-model-loader pattern for pre-baking nomic-embed-text into the image.

## Standard Stack

The established tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| s6-overlay | v3.2.2.0 | Process supervisor & init | Purpose-built for containers, proper PID 1 handling, dependency management, graceful shutdown |
| PostgreSQL | 16+ | Database | Official docker image, well-documented container patterns |
| Ollama | latest | Embedding generation | Official docker image, provides nomic-embed-text model |
| Python | 3.11-slim | MCP server runtime | Project standard, slim variant for smaller image |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pg_isready | (bundled with PostgreSQL) | PostgreSQL readiness check | Service dependency verification |
| curl | (install in image) | HTTP health checks | Ollama readiness, MCP health endpoint |
| execline | (bundled with s6) | Script execution | s6 service scripts for efficiency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| s6-overlay | supervisord | supervisord doesn't handle PID 1 properly, less accurate health status during failures |
| Multi-stage Ollama build | Runtime model pull | Runtime pull slow (274MB+ download), fails in air-gapped environments |
| SIGINT for PostgreSQL | SIGTERM (default) | SIGTERM waits for clients to disconnect, can hang indefinitely in container shutdown |

**Note:** Per CONTEXT.md, s6-overlay is the chosen process supervisor (Claude's discretion area, now locked).

## Architecture Patterns

### Recommended Container Structure
```
/
├── init                          # s6-overlay entrypoint
├── etc/
│   └── s6-overlay/
│       ├── s6-rc.d/             # Service definitions
│       │   ├── user/
│       │   │   └── contents.d/
│       │   │       ├── svc-postgresql    # (empty file)
│       │   │       ├── svc-ollama        # (empty file)
│       │   │       └── svc-mcp           # (empty file)
│       │   ├── svc-postgresql/
│       │   │   ├── type                  # "longrun"
│       │   │   ├── run                   # start PostgreSQL
│       │   │   ├── finish                # cleanup on stop
│       │   │   ├── notification-fd       # "3" for readiness
│       │   │   ├── data/
│       │   │   │   └── check             # pg_isready script
│       │   │   └── dependencies.d/
│       │   │       └── base              # (empty file)
│       │   ├── svc-ollama/
│       │   │   ├── type                  # "longrun"
│       │   │   ├── run                   # start Ollama serve
│       │   │   ├── notification-fd       # "3" for readiness
│       │   │   ├── data/
│       │   │   │   └── check             # curl /api/tags
│       │   │   └── dependencies.d/
│       │   │       └── base              # (empty file)
│       │   ├── svc-mcp/
│       │   │   ├── type                  # "longrun"
│       │   │   ├── run                   # start MCP server
│       │   │   └── dependencies.d/
│       │   │       ├── svc-postgresql    # (empty file)
│       │   │       └── svc-ollama        # (empty file)
│       │   └── init-warmup/
│       │       ├── type                  # "oneshot"
│       │       ├── up                    # path to warmup script
│       │       └── dependencies.d/
│       │           └── svc-ollama        # (empty file)
│       └── scripts/
│           ├── warmup-ollama             # Ollama model warmup script
│           └── health-check              # Combined health check
├── data/                          # Persistent volume mount point
│   ├── pg_data/                  # PostgreSQL data directory
│   ├── ollama_models/            # Ollama model storage
│   └── cocosearch/               # CocoSearch state
├── mnt/
│   └── repos/                    # Read-only codebase mount point
└── app/                          # Application code
    └── cocosearch/
```

### Pattern 1: s6-rc Service Dependencies
**What:** Services declare dependencies via empty files in `dependencies.d/` directory
**When to use:** When service B must wait for service A to be ready before starting
**Example:**
```bash
# Source: https://github.com/just-containers/s6-overlay/blob/master/README.md
# Create MCP service that depends on PostgreSQL and Ollama
mkdir -p /etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d
touch /etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/svc-postgresql
touch /etc/s6-overlay/s6-rc.d/svc-mcp/dependencies.d/svc-ollama
```

### Pattern 2: Readiness Notification with s6-notifyoncheck
**What:** Use polling-based readiness for services without native notification
**When to use:** PostgreSQL and Ollama don't natively notify s6 when ready
**Example:**
```bash
# /etc/s6-overlay/s6-rc.d/svc-postgresql/run
#!/command/execlineb -P
# Source: https://skarnet.org/software/s6/s6-notifyoncheck.html

# notification-fd must be "3" in the service directory
s6-notifyoncheck -d -n 60 -s 1000 -w 5000
postgres -D /data/pg_data
```

```bash
# /etc/s6-overlay/s6-rc.d/svc-postgresql/data/check
#!/bin/sh
# Returns 0 when PostgreSQL is ready
exec pg_isready -h localhost -U postgres
```

### Pattern 3: Multi-Stage Build for Model Pre-loading
**What:** Pre-download Ollama model during Docker build, not at runtime
**When to use:** Always - avoids 274MB+ download at container start
**Example:**
```dockerfile
# Source: https://dev.to/jensgst/preloading-ollama-models-221k
FROM gerke74/ollama-model-loader as downloader
RUN /ollama-pull nomic-embed-text

FROM ollama/ollama as ollama-base
COPY --from=downloader /root/.ollama /root/.ollama
```

### Pattern 4: PostgreSQL Fast Shutdown with SIGINT
**What:** Send SIGINT instead of SIGTERM to PostgreSQL for predictable shutdown
**When to use:** Always in containers - prevents indefinite wait for client disconnection
**Example:**
```bash
# In s6 finish script or use container stop signal
# Source: https://github.com/docker-library/postgres/issues/714
# SIGINT = Fast Shutdown: aborts transactions, exits promptly
# SIGTERM = Smart Shutdown: waits for all sessions to end (can hang forever)

# Option 1: In Dockerfile for the whole container
STOPSIGNAL SIGINT

# Option 2: In s6 service finish script for PostgreSQL specifically
#!/command/execlineb -S0
foreground { pg_ctl stop -D /data/pg_data -m fast }
```

### Anti-Patterns to Avoid
- **Shell form CMD in Dockerfile:** Use exec form `["python", "-m", "..."]` not `python -m ...` - shell form doesn't receive signals properly
- **SIGTERM for PostgreSQL:** Will wait indefinitely for clients to disconnect, causing container shutdown timeouts
- **Runtime model download:** Slow startup (30-120s for Ollama), breaks air-gapped environments
- **Single healthcheck for multi-service:** Need tiered health status (starting/healthy/unhealthy) based on which services are up
- **Legacy /etc/services.d format:** Use modern /etc/s6-overlay/s6-rc.d for proper dependency management

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process supervision | Custom bash script with traps | s6-overlay | Proper PID 1, zombie reaping, signal forwarding, dependency ordering |
| PostgreSQL readiness | Sleep loop | pg_isready + s6-notifyoncheck | pg_isready checks actual connection acceptance, not just process running |
| Service dependencies | Hardcoded sleeps | s6-rc dependencies.d | Declarative, handles restart ordering, properly waits for readiness |
| Container init | bash entrypoint.sh | s6-overlay /init | Proper signal handling, clean shutdown, supports multiple services |
| Model embedding | Runtime `ollama pull` | gerke74/ollama-model-loader multi-stage | Build-time download, consistent startup time |
| Graceful shutdown | Manual SIGTERM handling | s6 finish scripts + S6_KILL_GRACETIME | s6 handles cascading shutdown in correct dependency order |

**Key insight:** Process supervision in containers is deceptively complex. PID 1 must handle signals, reap zombies, and coordinate shutdown order. s6-overlay handles all of this correctly.

## Common Pitfalls

### Pitfall 1: PostgreSQL Data Corruption on Container Stop
**What goes wrong:** Container times out waiting for PostgreSQL to stop, gets SIGKILL, data corruption
**Why it happens:** Docker sends SIGTERM which triggers "Smart Shutdown" waiting for clients to disconnect
**How to avoid:** Use SIGINT (Fast Shutdown) or configure longer stop timeout with `docker stop -t 60`
**Warning signs:** "database system was not properly shut down" messages on restart

### Pitfall 2: Ollama Cold Start Latency
**What goes wrong:** First embedding request takes 30-120 seconds
**Why it happens:** Model loading from disk to memory on first request
**How to avoid:** Add warmup oneshot service that sends empty request after Ollama ready
**Warning signs:** Slow first request, fast subsequent requests

### Pitfall 3: Services Starting Before Dependencies Ready
**What goes wrong:** MCP server fails to connect to PostgreSQL, then crashes
**Why it happens:** "up" doesn't mean "ready" - process started but not accepting connections
**How to avoid:** Use readiness notification (notification-fd + check script) not just process start
**Warning signs:** Connection refused errors in logs during startup

### Pitfall 4: s6 Oneshot Script Format Confusion
**What goes wrong:** Oneshot service doesn't run, or runs with wrong interpreter
**Why it happens:** The `up` file is a command line, not a script - shebangs are ignored
**How to avoid:** Put actual script in /etc/s6-overlay/scripts/, reference path in `up` file
**Warning signs:** "file not found" errors, wrong shell interpreting script

### Pitfall 5: Signals Lost in Shell-Form CMD
**What goes wrong:** Container doesn't stop gracefully on `docker stop`
**Why it happens:** Shell form `CMD command args` runs via /bin/sh which doesn't forward signals
**How to avoid:** Use exec form `CMD ["command", "args"]` or exec into the command from shell
**Warning signs:** Container always times out on stop, processes don't see SIGTERM

### Pitfall 6: Health Check Fails During Startup
**What goes wrong:** Container marked unhealthy before services fully started
**Why it happens:** Health check starts immediately, services take time to initialize
**How to avoid:** Use `--start-period` in HEALTHCHECK to ignore failures during startup grace period
**Warning signs:** Container restarts during startup, health flapping

## Code Examples

Verified patterns from official sources:

### s6-overlay Installation in Dockerfile
```dockerfile
# Source: https://github.com/just-containers/s6-overlay/blob/master/README.md
FROM python:3.11-slim

ARG S6_OVERLAY_VERSION=3.2.2.0
ARG TARGETARCH

# Install s6-overlay
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${TARGETARCH}.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    tar -C / -Jxpf /tmp/s6-overlay-${TARGETARCH}.tar.xz && \
    rm /tmp/s6-overlay-*.tar.xz

ENTRYPOINT ["/init"]
```

### PostgreSQL Longrun Service
```bash
# /etc/s6-overlay/s6-rc.d/svc-postgresql/type
longrun
```

```bash
# /etc/s6-overlay/s6-rc.d/svc-postgresql/run
#!/command/execlineb -P
# Source: https://skarnet.org/software/s6/s6-notifyoncheck.html
s6-notifyoncheck -d -n 60 -s 1000 -w 5000 -c /etc/s6-overlay/s6-rc.d/svc-postgresql/data/check
exec postgres -D /data/pg_data
```

```bash
# /etc/s6-overlay/s6-rc.d/svc-postgresql/data/check
#!/bin/sh
# Source: https://github.com/peter-evans/docker-compose-healthcheck
exec pg_isready -h localhost -U postgres
```

```bash
# /etc/s6-overlay/s6-rc.d/svc-postgresql/notification-fd
3
```

### Ollama Longrun Service with Readiness Check
```bash
# /etc/s6-overlay/s6-rc.d/svc-ollama/type
longrun
```

```bash
# /etc/s6-overlay/s6-rc.d/svc-ollama/run
#!/command/execlineb -P
s6-notifyoncheck -d -n 120 -s 2000 -w 10000 -c /etc/s6-overlay/s6-rc.d/svc-ollama/data/check
exec ollama serve
```

```bash
# /etc/s6-overlay/s6-rc.d/svc-ollama/data/check
#!/bin/sh
# Source: https://github.com/ollama/ollama/issues/1378
curl -sf http://localhost:11434/api/tags > /dev/null 2>&1
```

### Model Warmup Oneshot
```bash
# /etc/s6-overlay/s6-rc.d/init-warmup/type
oneshot
```

```bash
# /etc/s6-overlay/s6-rc.d/init-warmup/up
/etc/s6-overlay/scripts/warmup-ollama
```

```bash
# /etc/s6-overlay/scripts/warmup-ollama (executable)
#!/bin/sh
# Source: https://docs.ollama.com/faq
# Preload model into memory with empty request
MODEL=${COCOSEARCH_EMBED_MODEL:-nomic-embed-text}
echo "Warming up Ollama model: $MODEL"
curl -sf http://localhost:11434/api/embeddings -d "{\"model\": \"$MODEL\", \"prompt\": \"warmup\"}" > /dev/null
echo "Ollama model warm-up complete"
```

### Docker HEALTHCHECK with Start Period
```dockerfile
# Source: https://lumigo.io/container-monitoring/docker-health-check-a-practical-guide/
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD /etc/s6-overlay/scripts/health-check || exit 1
```

```bash
# /etc/s6-overlay/scripts/health-check
#!/bin/sh
# Tiered health check - returns 0 only when all services ready

# Check PostgreSQL
pg_isready -h localhost -U postgres > /dev/null 2>&1 || exit 1

# Check Ollama
curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 || exit 1

# Check MCP server
curl -sf http://localhost:${COCOSEARCH_MCP_PORT:-3000}/health > /dev/null 2>&1 || exit 1

exit 0
```

### Environment Variable Configuration
```dockerfile
# Environment variables from CONTEXT.md decisions
ENV COCOSEARCH_MCP_PORT=3000 \
    COCOSEARCH_PG_PORT=5432 \
    COCOSEARCH_OLLAMA_PORT=11434 \
    COCOSEARCH_EMBED_MODEL=nomic-embed-text \
    COCOSEARCH_MCP_TRANSPORT=streamable-http \
    COCOSEARCH_LOG_LEVEL=warn \
    OLLAMA_HOST=0.0.0.0:11434 \
    PGDATA=/data/pg_data \
    OLLAMA_MODELS=/data/ollama_models \
    S6_KILL_GRACETIME=10000 \
    S6_SERVICES_GRACETIME=10000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| supervisord for multi-process | s6-overlay | ~2020 | Proper PID 1 handling, accurate health status |
| /etc/services.d (s6 v2) | /etc/s6-overlay/s6-rc.d (s6 v3) | v3 release | Proper dependency management between services |
| Runtime `ollama pull` | Multi-stage build with model baking | 2024+ | Consistent startup time, air-gapped support |
| SIGTERM for PostgreSQL | SIGINT (PR #763 merged) | Jan 2024 | Fast predictable shutdown, prevents data corruption |
| Single process per container | One thing per container | philosophical shift | Multi-service containers acceptable for cohesive apps |

**Deprecated/outdated:**
- **/etc/services.d pattern:** Still works but lacks dependency management, use s6-rc.d instead
- **supervisord in containers:** Poor PID 1 handling, doesn't propagate failure state to orchestrator
- **docker-compose with wait-for-it:** Fragile, better to use s6-rc dependencies inside single container

## Open Questions

Things that couldn't be fully resolved:

1. **nomic-embed-text exact model size in image**
   - What we know: Model is ~274MB, uses 2-4GB RAM at runtime
   - What's unclear: Exact size impact on final Docker image
   - Recommendation: Build image, verify size, document in README

2. **s6-notifyoncheck timing parameters**
   - What we know: -n (attempts), -s (sleep ms), -w (timeout ms) control polling
   - What's unclear: Optimal values for PostgreSQL and Ollama startup times
   - Recommendation: Start with documented values, tune based on testing

3. **Tiered healthcheck state reporting**
   - What we know: Docker only has healthy/unhealthy/starting states
   - What's unclear: How to report "PostgreSQL ready, Ollama still starting"
   - Recommendation: Use start_period (60s+) to hide startup phase, consider custom /health endpoint with JSON status

## Sources

### Primary (HIGH confidence)
- [s6-overlay GitHub README](https://github.com/just-containers/s6-overlay) - Installation, service structure, dependencies
- [PostgreSQL Server Shutdown Documentation](https://www.postgresql.org/docs/current/server-shutdown.html) - Signal behavior
- [PostgreSQL Docker SIGINT PR #714](https://github.com/docker-library/postgres/issues/714) - SIGINT recommendation
- [Ollama FAQ](https://docs.ollama.com/faq) - Model preloading, environment variables
- [Docker HEALTHCHECK Documentation](https://lumigo.io/container-monitoring/docker-health-check-a-practical-guide/) - Configuration options

### Secondary (MEDIUM confidence)
- [s6-notifyoncheck](https://skarnet.org/software/s6/s6-notifyoncheck.html) - Readiness polling mechanism
- [Preloading Ollama Models](https://dev.to/jensgst/preloading-ollama-models-221k) - Multi-stage build pattern
- [pg_isready Health Check Pattern](https://github.com/peter-evans/docker-compose-healthcheck) - PostgreSQL readiness

### Tertiary (LOW confidence)
- [Ollama Health Check Endpoint](https://github.com/ollama/ollama/issues/1378) - /api/tags as health endpoint (not official, but community consensus)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation, well-established patterns
- Architecture: HIGH - s6-overlay v3 documentation is comprehensive
- Pitfalls: HIGH - Multiple GitHub issues document these problems with solutions
- Code examples: MEDIUM - Patterns verified against docs, not runtime tested

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - s6-overlay stable, patterns well-established)
