# Domain Pitfalls

**Domain:** All-in-One Docker Deployment + MCP Transport Support
**Researched:** 2026-02-01
**Milestone:** v2.0 -- Docker Image + MCP SSE/Streamable HTTP
**Confidence:** HIGH

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or fundamental architecture failures.

### Pitfall 1: PID 1 Signal Handling Breaks Graceful Shutdown

**What goes wrong:**
In a multi-service container (PostgreSQL + Ollama + Python app), the entrypoint process runs as PID 1. If that process is a shell script or the Python app itself, SIGTERM signals from `docker stop` are silently ignored. Docker waits 10 seconds, then sends SIGKILL, forcefully terminating all processes. PostgreSQL has no chance to flush WAL buffers, potentially corrupting the database.

**Why it happens:**
- Linux kernel treats PID 1 specially: signals are ignored unless explicitly handled
- Shell scripts (`#!/bin/bash`) don't forward signals to child processes by default
- Python's default signal handlers don't propagate to subprocess children
- Docker's `docker stop` sends SIGTERM, waits `--stop-timeout` (default 10s), then SIGKILL
- PostgreSQL needs SIGTERM to initiate "smart shutdown" (wait for clients, flush buffers)
- Ollama may be mid-inference when killed, leaving GPU memory in bad state

**Consequences:**
- PostgreSQL database corruption on container restart
- "invalid record length" errors in PostgreSQL WAL recovery
- Lost indexed data requiring full re-index
- Ollama model files corrupted mid-download
- Users experience data loss after routine container restarts

**Warning signs:**
- Container takes exactly 10 seconds to stop (hitting SIGKILL timeout)
- PostgreSQL logs showing recovery on every startup
- Ollama re-downloading models after container restart
- "database was not properly shut down" messages

**Prevention:**
1. Use a proper init system as PID 1: [tini](https://github.com/krallin/tini) or [dumb-init](https://github.com/Yelp/dumb-init)
2. If using Docker 1.13+, use `--init` flag: `docker run --init ...`
3. Embed tini in the image: `ENTRYPOINT ["/tini", "--", "/entrypoint.sh"]`
4. Use supervisord with `stopwaitsecs` configured for each service
5. Implement explicit signal handlers in entrypoint script using `trap`
6. Set `stop_grace_period: 30s` in docker-compose for PostgreSQL to complete shutdown
7. Test with `docker stop --time=1` to verify graceful handling under time pressure

**Detection strategy:**
```bash
# Time how long docker stop takes - should be < 10s for graceful shutdown
time docker stop cocosearch-all-in-one
# Check PostgreSQL startup logs for recovery mode
docker logs cocosearch-all-in-one 2>&1 | grep -i "recovery"
```

**Phase to address:** Phase 1 (Container foundation) -- must be correct before adding any services.

---

### Pitfall 2: MCP stdio Transport Corrupted by Logging to stdout

**What goes wrong:**
The existing CocoSearch MCP server logs to stderr (correctly configured in `server.py`), but adding SSE/HTTP transport requires additional dependencies that may log to stdout. Third-party libraries (httpx, uvicorn, starlette) default to stdout logging. Any non-JSON-RPC output to stdout corrupts the protocol stream, causing the MCP client to disconnect with cryptic parsing errors.

**Why it happens:**
- MCP stdio transport uses stdout exclusively for JSON-RPC messages
- The [MCP specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) states: "The server MUST NOT write anything to its stdout that is not a valid MCP message"
- Uvicorn's default logging goes to stdout
- Third-party libraries may use `print()` or `logging.basicConfig()` with default stdout
- Python warnings module defaults to stderr but some libraries override this
- CocoIndex's internal logging may write to stdout during initialization

**Consequences:**
- MCP client reports "invalid JSON" or "unexpected token" errors
- Connection drops silently with no clear error message
- Intermittent failures when libraries log only on certain code paths
- Extremely difficult to debug (logs themselves cause the problem)

**Warning signs:**
- MCP client shows "malformed messages" error
- Protocol works with simple tools, fails with complex operations
- Adding new dependencies breaks previously working stdio transport
- Claude Code reports "MCP server disconnected" without explanation

**Prevention:**
1. Keep the existing stderr logging configuration at the very top of server.py (before imports)
2. When adding HTTP transport, configure uvicorn explicitly: `log_config=None` or custom config to stderr
3. Audit all new dependencies for stdout usage: `grep -r "print(" vendor_code/`
4. Add CI test that captures stdout and fails if any non-JSON-RPC output appears
5. Use `contextlib.redirect_stdout` to stderr during library initialization
6. Test stdio transport with MCP Inspector after every dependency addition
7. Consider using `PYTHONUNBUFFERED=1` to catch buffered stdout issues early

**Detection strategy (automated test):**
```python
def test_stdio_purity():
    """Verify no stdout pollution during MCP operations."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "cocosearch.mcp"],
        input='{"jsonrpc":"2.0","method":"initialize","id":1}',
        capture_output=True, text=True, timeout=5
    )
    # Every line of stdout must be valid JSON
    for line in result.stdout.strip().split('\n'):
        if line:
            json.loads(line)  # Raises if not JSON
```

**Phase to address:** Throughout -- every phase adding code must maintain stdout purity.

---

### Pitfall 3: PostgreSQL Initialization Scripts Silently Skipped

**What goes wrong:**
PostgreSQL Docker images run scripts in `/docker-entrypoint-initdb.d/` only when the data directory is empty. In an all-in-one container with a persistent volume, the volume survives container recreation. On container update/restart, the init scripts don't run, and users don't get the pgvector extension or schema updates. The application fails with "extension pgvector does not exist."

**Why it happens:**
- PostgreSQL official image design: init scripts run once, on first start with empty data dir
- [Docker PostgreSQL docs](https://hub.docker.com/_/postgres/): "Scripts in /docker-entrypoint-initdb.d are only run if you start the container with a data directory that is empty"
- Persistent volumes for data durability mean data dir is never empty after first run
- Schema migrations require running SQL, but init scripts won't re-run
- PostgreSQL 18+ changed volume structure (data is now a symlink), breaking some bind mounts

**Consequences:**
- pgvector extension not created after container update
- Schema migrations not applied
- Application crashes with missing extension/table errors
- Users must manually run SQL or wipe their data volume
- "It worked before the update" -- classic regression

**Warning signs:**
- Init scripts have correct content but weren't executed
- Extension exists in dev (fresh volume) but not in prod (existing volume)
- Application errors about missing tables/extensions after container update
- Init script timestamps show old dates despite recent container builds

**Prevention:**
1. Don't rely solely on init scripts for required schema -- implement application-level migrations
2. Check extension existence at startup and create if missing: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Use CocoIndex's `flow.setup()` for table creation (it already handles schema evolution)
4. For critical init (pgvector extension), add a startup check in the entrypoint script
5. Document that users must wipe volumes when upgrading major PostgreSQL versions
6. Test upgrade path: create container with v1, update to v2, verify everything works

**Startup check pattern:**
```bash
# entrypoint.sh
wait_for_postgres() {
    until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
        sleep 1
    done
}

ensure_extensions() {
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"
}

start_postgres &
wait_for_postgres
ensure_extensions
```

**Phase to address:** Phase 1 (Container foundation) -- PostgreSQL setup must be robust from the start.

---

### Pitfall 4: Ollama Cold Start Blocks Application Startup

**What goes wrong:**
Ollama in Docker must download models before serving embeddings. For the nomic-embed-text model (~274MB), this takes 30-120 seconds depending on network speed. The all-in-one container's healthcheck passes when Ollama responds to `ollama list`, but the model isn't loaded. CocoSearch tries to generate embeddings, times out, and fails with cryptic errors. Users see "connection refused" or timeout errors on first use.

**Why it happens:**
- Ollama starts its HTTP server before downloading any models
- `ollama list` healthcheck returns success even with no models
- Model download happens on first API call, not at startup
- First embedding request triggers download, which times out the request
- [GitHub issue #6006](https://github.com/ollama/ollama/issues/6006): "Docker version of Ollama model loads slowly"
- On HDD-backed volumes, model loading takes 3x longer due to I/O contention

**Consequences:**
- First search/index operation fails with timeout
- Users must wait silently for model download with no progress indication
- Retry logic may hammer Ollama, further slowing download
- Container appears healthy but is unusable
- Terrible first-run experience

**Warning signs:**
- Container healthcheck passes but operations fail
- First operation takes 1-2 minutes, subsequent operations are fast
- `ollama list` shows no models immediately after container start
- High CPU/network usage with no apparent progress feedback

**Prevention:**
1. Pull model in entrypoint script before marking container ready:
   ```bash
   ollama serve &
   until curl -s http://localhost:11434 > /dev/null; do sleep 1; done
   ollama pull nomic-embed-text
   ```
2. Use healthcheck that verifies model availability, not just Ollama server:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
     # AND parse response to verify nomic-embed-text is present
   ```
3. Pre-bake model into Docker image (see Pitfall 5 for tradeoffs)
4. Display download progress in container logs
5. Add startup banner showing "Downloading embedding model... X%"
6. Configure longer timeouts for first embedding operation
7. Implement warm-up call at container start: send empty embedding request to load model into memory

**Phase to address:** Phase 1 (Container foundation) -- startup sequence must handle model readiness.

---

### Pitfall 5: Baking Ollama Model into Image Creates 4GB+ Images

**What goes wrong:**
To avoid cold-start download, developers bake the embedding model into the Docker image. The nomic-embed-text model is ~274MB, but Ollama stores model layers inefficiently. Combined with the Ollama binary (~800MB), Python dependencies, and PostgreSQL, the image balloons to 4-5GB. Image pulls take 10+ minutes, CI/CD pipelines time out, and registry storage costs explode.

**Why it happens:**
- Ollama official image is ~800MB (includes CUDA support)
- Model files stored in `/root/.ollama/models/` as multiple blob layers
- Docker layer caching doesn't help -- model blobs are large single files
- Each image update re-pushes the entire model layer
- No way to share model layers between image versions
- [Medium article](https://towardsdatascience.com/reducing-the-size-of-docker-images-serving-llm-models-b70ee66e5a76/): "A 1GB model increases to 8GB when deployed using Docker"

**Consequences:**
- 10+ minute image pull times
- CI/CD pipeline failures due to timeout
- Expensive registry storage
- Slow deployment rollbacks
- Users abandon the tool due to download times

**Warning signs:**
- Docker build takes 20+ minutes
- `docker images` shows 4GB+ image size
- Pull progress shows single large layer downloading slowly
- Registry storage costs increasing rapidly

**Prevention:**
1. **Don't bake models** -- use volume mount for `/root/.ollama` with lazy download
2. If baking, use alpine/ollama base (~70MB) instead of official (~800MB)
3. Use multi-stage build to minimize Python dependencies
4. Compress model files in image, decompress at runtime (trades startup time for image size)
5. Consider separate "model sidecar" container that shares volume with main container
6. Use image layer optimization: `--squash` flag or BuildKit optimizations
7. Document expected image size in README so users know what to expect
8. Provide both "full" (with model) and "lite" (download at runtime) image variants

**Size budget recommendation:**
| Component | Target Size |
|-----------|-------------|
| Base OS (Alpine) | ~50MB |
| Python + deps | ~200MB |
| PostgreSQL | ~100MB |
| Ollama (alpine) | ~70MB |
| Application code | ~10MB |
| **Total (no model)** | **~450MB** |
| With baked model | +300MB = ~750MB |

**Phase to address:** Phase 2 (Image optimization) -- after basic functionality works.

---

### Pitfall 6: SSE Transport Deprecated, Users on Legacy Clients Can't Connect

**What goes wrong:**
MCP SSE transport was deprecated in spec version 2025-03-26 in favor of Streamable HTTP. CocoSearch implements only the new Streamable HTTP transport. Users with older MCP clients (pre-2025 Claude Desktop, older integrations) can't connect at all. They get HTTP 404 or 405 errors with no helpful message about upgrading.

**Why it happens:**
- [MCP specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports): "SSE Transport has been deprecated"
- MCP ecosystem fragmented: different clients upgraded at different times
- SSE used two endpoints (GET for SSE stream, POST for messages); Streamable HTTP uses one
- Transport negotiation is not automatic -- client must know which transport to use
- Claude Code updated quickly, but third-party MCP clients lag behind

**Consequences:**
- "It works in Claude Code but not in my custom client"
- Users file bugs about connection failures
- Support burden explaining SSE deprecation
- Users abandon CocoSearch for tools that still support SSE

**Warning signs:**
- Users reporting "connection refused" with specific MCP clients
- HTTP 404/405 errors in server logs from SSE endpoint paths
- Feature requests asking for "SSE support"
- GitHub issues from users of older Claude Desktop versions

**Prevention:**
1. Implement both transports during transition period:
   - Streamable HTTP on `/mcp` (primary)
   - Legacy SSE on `/sse` (deprecated, with warning headers)
2. Use [Supergateway](https://github.com/supercorp-ai/supergateway) as SSE-to-stdio proxy for legacy clients
3. Add clear error message when SSE endpoint hit: "SSE transport deprecated, use Streamable HTTP"
4. Document supported transports and minimum client versions
5. Log warnings when SSE endpoint accessed to track adoption
6. Plan SSE removal timeline: warn now, remove in 6 months

**Transport implementation strategy:**
```python
# Support both during transition
@app.route('/mcp', methods=['POST', 'GET'])
async def streamable_http():
    """Modern Streamable HTTP transport."""
    ...

@app.route('/sse')
async def legacy_sse():
    """Deprecated SSE transport - warn and serve."""
    response.headers['X-Deprecation'] = 'SSE transport deprecated, use /mcp'
    ...
```

**Phase to address:** Phase 3 (Transport implementation) -- design must account for both transports.

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or degraded user experience.

### Pitfall 7: MCP Working Directory Not Propagated to Container

**What goes wrong:**
When CocoSearch MCP server runs in Docker, it has no knowledge of the host's working directory. The `index_codebase(path="/code")` tool receives paths relative to the container, not the user's actual project. Users must manually figure out volume mappings and translate paths. Auto-detection of "current project" is impossible.

**Why it happens:**
- Docker containers have isolated filesystems
- No standard MCP mechanism for passing client CWD to server
- [GitHub Issue #1520](https://github.com/modelcontextprotocol/python-sdk/issues/1520): "How to access the current working directory when an MCP server is launched"
- Volume mounts map host paths to container paths, but mapping is configurable
- Users may mount at `/code`, `/app`, `/workspace`, or any arbitrary path
- `os.getcwd()` in container returns container's cwd, not host's

**Consequences:**
- Path confusion: "index /Users/me/project" fails because container sees "/code"
- Users must remember their volume mapping
- Can't implement "index current directory" convenience feature
- Error messages show container paths, confusing users
- Multi-project users must manually specify index names

**Warning signs:**
- User confusion about which path to provide
- "File not found" errors with paths that exist on host
- Users asking "what path do I use?"
- Index names defaulting to "code" for every project (from mount point)

**Prevention:**
1. Require `PROJECT_ROOT` environment variable in docker run:
   ```bash
   docker run -v /Users/me/project:/code -e PROJECT_ROOT=/Users/me/project ...
   ```
2. Store both container path and original host path in index metadata
3. Auto-detect common mount patterns: if cwd is `/code`, check `PROJECT_ROOT` env
4. Add helper tool `detect_project()` that reads `.git/config` or `package.json` for project name
5. Derive index name from git remote URL or directory name, not mount point
6. Document required environment variables prominently

**Index name derivation logic:**
```python
def derive_index_name(container_path: str) -> str:
    """Derive index name from project, not mount point."""
    # Check for git remote
    git_config = Path(container_path) / ".git" / "config"
    if git_config.exists():
        # Parse remote URL for repo name
        ...
    # Fall back to PROJECT_ROOT env var
    if host_path := os.environ.get("PROJECT_ROOT"):
        return Path(host_path).name
    # Last resort: use mount point name (not ideal)
    return Path(container_path).name
```

**Phase to address:** Phase 2 (Docker integration) -- path mapping must be designed before tools work correctly.

---

### Pitfall 8: Service Startup Order Race Conditions

**What goes wrong:**
In an all-in-one container, PostgreSQL, Ollama, and the Python app start concurrently (or via supervisord in rapid succession). The Python app tries to connect to PostgreSQL before it's ready, or calls Ollama before model is loaded. Retry logic helps but adds startup latency and complexity. Users see intermittent "connection refused" errors.

**Why it happens:**
- Supervisord starts all services simultaneously by default
- PostgreSQL takes 5-10 seconds to initialize on first run
- Ollama model download/load takes 30+ seconds
- Python app starts in ~1 second and immediately tries connections
- [Docker docs](https://docs.docker.com/compose/how-tos/startup-order/): "Compose does not wait until a container is 'ready'"
- Health checks help in Compose but don't exist inside a single container

**Consequences:**
- Intermittent startup failures
- App crashes on first connection attempt
- Confusing error messages about connection refused
- Users restart container multiple times before it works
- Retry loops waste startup time

**Warning signs:**
- Container logs show "connection refused" then later success
- Startup time varies widely (5s to 60s)
- `docker logs` shows PostgreSQL still initializing when app tries to connect
- supervisord shows app process restarting during startup

**Prevention:**
1. Implement explicit startup sequencing in entrypoint script:
   ```bash
   # 1. Start PostgreSQL, wait for ready
   pg_ctl start && until pg_isready; do sleep 1; done
   # 2. Start Ollama, wait for ready + model loaded
   ollama serve & until ollama list | grep nomic; do sleep 1; done
   # 3. Start Python app
   exec python -m cocosearch.mcp
   ```
2. Use supervisord with `priority` settings (lower = start earlier)
3. Implement connection retry with exponential backoff in Python app
4. Add explicit dependency checks at app startup (before serving requests)
5. Use health check that verifies all services are ready
6. Log startup phase clearly: "Waiting for PostgreSQL... Waiting for Ollama... Ready"

**Supervisord priority example:**
```ini
[program:postgres]
priority=100  ; Start first
command=/usr/lib/postgresql/17/bin/postgres

[program:ollama]
priority=200  ; Start after postgres
command=/usr/bin/ollama serve
startsecs=30  ; Wait for model load

[program:cocosearch]
priority=300  ; Start last
command=python -m cocosearch.mcp
```

**Phase to address:** Phase 1 (Container foundation) -- startup sequence is foundational.

---

### Pitfall 9: Supervisord Doesn't Exit on Service Failure

**What goes wrong:**
Supervisord keeps running even when critical services (PostgreSQL) crash. The container stays "running" but is non-functional. Docker healthcheck may pass (supervisord responds) even though PostgreSQL is down. Orchestrators like Kubernetes don't restart the container because it appears healthy.

**Why it happens:**
- Supervisord is designed to be a long-running process manager, not a one-shot init
- By default, supervisord restarts failed processes rather than exiting
- Even with `autorestart=false`, supervisord itself doesn't exit
- Container health is based on PID 1 (supervisord), not application health
- Zombie processes from crashed services accumulate

**Consequences:**
- Container appears healthy but doesn't work
- Kubernetes doesn't trigger restart
- Users manually restart containers repeatedly
- Resource leaks from zombie processes
- Monitoring shows green even during outages

**Warning signs:**
- Supervisord running but `supervisorctl status` shows services STOPPED
- Container uptime increasing but service unavailable
- `docker top` shows zombie processes
- Memory usage growing over time (zombie accumulation)

**Prevention:**
1. Use supervisord's `eventlistener` to exit on critical service failure:
   ```ini
   [eventlistener:exit_on_fatal]
   command=kill -SIGTERM 1
   events=PROCESS_STATE_FATAL
   ```
2. Configure health check to verify actual service, not just supervisord
3. Consider alternatives: s6-overlay handles this better by design
4. Use `supervisorctl shutdown` in eventlistener instead of kill
5. Set `startsecs=10` to avoid flapping detection during startup
6. Monitor for FATAL state in logs and alert

**s6-overlay alternative:**
```dockerfile
# s6-overlay automatically exits if service marked as "essential" dies
FROM base
ADD https://github.com/just-containers/s6-overlay/releases/.../s6-overlay.tar.gz /
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2  # Exit container on service failure
```

**Phase to address:** Phase 1 (Container foundation) -- process supervision design affects everything.

---

### Pitfall 10: Dual Transport Mode Creates Maintenance Burden

**What goes wrong:**
Supporting both stdio transport (for local Claude Code) and HTTP/SSE transport (for remote access) requires different code paths: stdio uses stdin/stdout, HTTP uses request/response. Bugs in one transport don't appear in the other. Test coverage must cover both. Features added to one transport are forgotten in the other.

**Why it happens:**
- stdio transport: synchronous, line-delimited JSON-RPC on stdin/stdout
- HTTP transport: async, request/response or SSE streaming
- Different error handling (stdio crashes silently, HTTP returns error responses)
- Different authentication (stdio is implicitly trusted, HTTP needs auth)
- Different deployment (stdio via CLI, HTTP via server)
- MCP Python SDK abstracts some but not all transport differences

**Consequences:**
- Bug fixes applied to one transport, not the other
- Test matrix explosion (each feature x each transport)
- User confusion about which transport to use
- "Works locally but not remotely" support tickets
- Codebase complexity grows with transport-specific branches

**Warning signs:**
- Tests pass on stdio, fail on HTTP (or vice versa)
- Feature works in Claude Code but not in web client
- `if transport == "stdio"` conditionals spreading through codebase
- HTTP transport missing features that stdio has

**Prevention:**
1. Implement tool logic once, transport layer wraps it:
   ```python
   # tools.py - pure business logic, no transport awareness
   def search_code(query: str, index_name: str) -> list[dict]:
       ...

   # stdio_transport.py - wraps tools for stdio
   # http_transport.py - wraps tools for HTTP
   ```
2. Use MCP SDK's transport abstraction consistently
3. Write transport-agnostic integration tests that run against both
4. Document which transport supports which features
5. Feature parity checklist in PR template
6. Consider transport as configuration, not code branches

**Test strategy:**
```python
@pytest.mark.parametrize("transport", ["stdio", "http"])
def test_search_returns_results(transport, transport_client):
    """Same test runs against both transports."""
    client = transport_client(transport)
    result = client.call("search_code", {"query": "test", "index_name": "demo"})
    assert len(result) > 0
```

**Phase to address:** Phase 3 (Transport implementation) -- architecture must separate transport from logic.

---

### Pitfall 11: Volume Permissions Mismatch Between Host and Container

**What goes wrong:**
PostgreSQL runs as user `postgres` (UID 999), Ollama as `ollama` (UID 1000), Python as `root` or custom user. When host directories are mounted as volumes, file ownership doesn't match. PostgreSQL can't write to its data directory, Ollama can't save models, or indexed files aren't readable.

**Why it happens:**
- Linux file permissions based on UID/GID, not usernames
- Host UID 1000 (typical user) != container UID 999 (postgres)
- Docker doesn't translate UIDs between host and container
- macOS Docker Desktop uses VM, adding another layer of permission complexity
- SELinux/AppArmor may block access even with correct UIDs

**Consequences:**
- "Permission denied" errors on startup
- PostgreSQL refuses to start (data dir not owned by postgres)
- Ollama can't save downloaded models
- Works on one machine, fails on another
- Confusing errors about ownership

**Warning signs:**
- `ls -la` in container shows wrong ownership
- Startup errors mentioning permissions
- Works with `docker run --privileged` but not without
- macOS and Linux behave differently

**Prevention:**
1. Use named volumes (Docker manages permissions) instead of bind mounts for data:
   ```yaml
   volumes:
     postgres_data:  # Named volume - Docker handles permissions
   ```
2. For code directories (bind mounts), ensure consistent UID:
   ```dockerfile
   RUN useradd -u 1000 appuser  # Match typical host UID
   ```
3. Use `user` directive in compose to match host user
4. Initialize data directories with correct ownership in entrypoint
5. Document required host directory permissions
6. Add startup check that verifies write permissions to data directories

**Permission fix in entrypoint:**
```bash
# Fix permissions on mounted volumes
chown -R postgres:postgres /var/lib/postgresql/data
chown -R ollama:ollama /root/.ollama
```

**Phase to address:** Phase 1 (Container foundation) -- permissions must be correct before services start.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without major rework.

### Pitfall 12: Container Logs Interleave Service Output Chaotically

**What goes wrong:**
PostgreSQL, Ollama, and Python all write to container stdout/stderr. Logs interleave randomly, making debugging difficult. No way to filter by service. Log aggregation tools can't parse the mixed output.

**Prevention:**
1. Use supervisord's per-service log files: `stdout_logfile=/var/log/%(program_name)s.log`
2. Prefix each service's output with service name: `[postgres]`, `[ollama]`, `[app]`
3. For stdio transport, keep app logs on stderr only (stdout is protocol)
4. Provide `docker exec` commands to tail individual service logs
5. Consider structured logging (JSON) with service field

**Phase to address:** Phase 2 (Polish) -- nice to have, not blocking.

---

### Pitfall 13: HTTPS/TLS Not Configured for HTTP Transport

**What goes wrong:**
HTTP transport exposes an endpoint without TLS. In production, this means credentials (if any) transmitted in clear text. Reverse proxies or load balancers may require HTTPS upstream. Users deploy to cloud without realizing traffic is unencrypted.

**Prevention:**
1. Document that TLS termination should happen at reverse proxy (nginx, Cloudflare)
2. Optionally support `--tls-cert` and `--tls-key` flags for direct TLS
3. Add warning log if HTTP transport runs without TLS in non-localhost mode
4. Provide example nginx/Caddy config for TLS termination
5. Consider using Let's Encrypt integration for easy TLS

**Phase to address:** Phase 4 (Production hardening) -- not required for MVP.

---

### Pitfall 14: No Resource Limits Leads to OOM Kills

**What goes wrong:**
Ollama loads models into memory (~500MB for nomic-embed-text). PostgreSQL allocates shared buffers. Without memory limits, the container consumes available host memory and gets OOM-killed by the kernel. On systems with limited RAM (CI runners, small VMs), this happens frequently.

**Prevention:**
1. Document minimum memory requirements: 2GB recommended, 4GB for large indexes
2. Set default memory limits in docker-compose: `mem_limit: 2g`
3. Configure PostgreSQL `shared_buffers` appropriately (128MB for small setups)
4. Use Ollama's CPU-only mode for memory-constrained environments
5. Add startup check that warns if available memory is below threshold

**Phase to address:** Phase 2 (Docker optimization) -- important for CI and constrained environments.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Container foundation | PID 1 signal handling (Pitfall 1) | CRITICAL | Use tini/dumb-init as init |
| Container foundation | PostgreSQL init scripts skipped (Pitfall 3) | CRITICAL | App-level schema management |
| Container foundation | Service startup race (Pitfall 8) | MODERATE | Explicit startup sequencing |
| Container foundation | Supervisord no-exit (Pitfall 9) | MODERATE | Use s6-overlay or exit listener |
| Container foundation | Volume permissions (Pitfall 11) | MODERATE | Named volumes, UID alignment |
| Model/image optimization | Cold start blocks app (Pitfall 4) | CRITICAL | Entrypoint model pull |
| Model/image optimization | 4GB+ image size (Pitfall 5) | MODERATE | Volume mount, alpine base |
| Transport implementation | stdout corruption (Pitfall 2) | CRITICAL | stderr-only logging |
| Transport implementation | SSE deprecation (Pitfall 6) | MODERATE | Support both transports |
| Transport implementation | Dual transport burden (Pitfall 10) | MODERATE | Separate transport from logic |
| Docker integration | CWD not propagated (Pitfall 7) | MODERATE | PROJECT_ROOT env var |

---

## Technical Debt Patterns (v2.0 Specific)

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip tini, use bash PID 1 | Simpler Dockerfile | Data corruption on restart | Never |
| Bake model into image | No cold start | 4GB+ images, slow pulls | Only for airgapped deployments |
| stdio transport only | Simpler code | No remote access | MVP only |
| No TLS support | Faster development | Security concerns | Local-only deployments |
| Hardcode volume paths | Quick setup | Inflexible for users | Never; use env vars |
| Skip startup sequencing | Faster container start | Intermittent failures | Never |

---

## Recovery Strategies (v2.0 Specific)

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| PID 1 signal handling | LOW | Add tini to Dockerfile, rebuild |
| stdout logging corruption | LOW | Fix logging config, redeploy |
| PostgreSQL init skipped | MEDIUM | Run init SQL manually or wipe volume |
| Cold start timeout | LOW | Add model pull to entrypoint, rebuild |
| Image too large | MEDIUM | Refactor to volume-based model loading |
| SSE clients can't connect | LOW | Add legacy SSE endpoint |
| Service race conditions | LOW | Fix entrypoint sequencing, redeploy |
| Permission denied | LOW | Fix volume permissions, restart |

---

## "Looks Done But Isn't" Checklist (v2.0)

- [ ] **Graceful shutdown:** `docker stop` completes in <10 seconds without SIGKILL
- [ ] **PostgreSQL data persists:** Stop container, restart, verify data still present
- [ ] **Ollama model ready:** Container healthcheck passes only after model is loaded
- [ ] **stdio purity:** Run MCP stdio transport, capture stdout, verify only JSON-RPC
- [ ] **HTTP transport works:** Connect via HTTP from external client
- [ ] **Volume permissions:** Works on both macOS and Linux hosts
- [ ] **Startup sequence:** Fresh container starts reliably 10/10 times
- [ ] **Service failure handling:** Kill PostgreSQL process, verify container restarts or logs error
- [ ] **Image size:** `docker images` shows <1GB (or <500MB without baked model)
- [ ] **Multi-project:** Index two different projects, verify both searchable

---

## Sources

- [PID 1 Signal Handling in Docker](https://petermalmgren.com/signal-handling-docker/) - Peter Malmgren (HIGH confidence)
- [krallin/tini](https://github.com/krallin/tini) - Official tini GitHub (HIGH confidence)
- [Yelp/dumb-init](https://github.com/Yelp/dumb-init) - Official dumb-init GitHub (HIGH confidence)
- [MCP Transports Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) - Official MCP docs (HIGH confidence)
- [MCP stdio Transport Corruption Issue](https://github.com/ruvnet/claude-flow/issues/835) - Real-world bug report (HIGH confidence)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres/) - Official PostgreSQL Docker docs (HIGH confidence)
- [Docker Compose Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) - Official Docker docs (HIGH confidence)
- [Ollama Docker Hub](https://hub.docker.com/r/ollama/ollama) - Official Ollama Docker docs (HIGH confidence)
- [Ollama Cold Start Issues](https://github.com/ollama/ollama/issues/6006) - GitHub issue (HIGH confidence)
- [A Pull-first Ollama Docker Image](https://www.dolthub.com/blog/2025-03-19-a-pull-first-ollama-docker-image/) - DoltHub blog (MEDIUM confidence)
- [Reducing Docker Images for LLMs](https://towardsdatascience.com/reducing-the-size-of-docker-images-serving-llm-models-b70ee66e5a76/) - Towards Data Science (MEDIUM confidence)
- [MCP SSE to Streamable HTTP Migration](https://brightdata.com/blog/ai/sse-vs-streamable-http) - Bright Data blog (MEDIUM confidence)
- [MCP Working Directory Issue](https://github.com/modelcontextprotocol/python-sdk/issues/1520) - GitHub issue (HIGH confidence)
- [Supergateway SSE-to-stdio Proxy](https://github.com/supercorp-ai/supergateway) - GitHub project (HIGH confidence)
- [Supervisord Documentation](https://supervisord.org/) - Official supervisord docs (HIGH confidence)
- [s6-overlay for Containers](https://www.sliceofexperiments.com/p/s6-run-multiple-processes-in-your) - Slice of Experiments (MEDIUM confidence)

---

*Pitfalls research for: CocoSearch v2.0 (All-in-One Docker + MCP Transports)*
*Researched: 2026-02-01*
