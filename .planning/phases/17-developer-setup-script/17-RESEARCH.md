# Phase 17: Developer Setup Script - Research

**Researched:** 2026-01-31
**Domain:** Bash scripting, Docker orchestration, developer tooling
**Confidence:** HIGH

## Summary

Developer setup scripts are a foundational DevOps practice where a single command bootstraps all dependencies and services for a development environment. The gold standard is idempotent scripts that safely handle repeated runs, provide clear progress output, and fail fast with actionable error messages.

For CocoSearch's setup script, the standard stack involves:
- **Bash** with strict error handling (`set -euo pipefail`)
- **Docker Compose** with health checks and the `--wait` flag for service readiness
- **UV package manager** for Python dependency installation (already in project)
- **Trap handlers** for cleanup on failure or interruption

The context decisions specify Docker-only Ollama (not native), plain text output (no colors), and UV for package management. Modern Docker Compose (v2+) provides native `--wait` flag support, eliminating the need for custom wait scripts.

**Primary recommendation:** Use bash strict mode, Docker Compose health checks with `--wait`, trap handlers for cleanup, and idempotent patterns (check-before-act). Stream underlying tool output directly rather than buffering.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bash | 4.0+ | Shell scripting | Universal on Linux/macOS, excellent error handling with strict mode |
| Docker Compose | v2+ | Container orchestration | Built-in health checks and `--wait` flag, industry standard for multi-container dev environments |
| UV | Latest | Python package manager | Already adopted in CocoSearch project, 10-100x faster than pip, handles venvs automatically |
| Docker CLI | Latest | Container runtime | Check daemon status, inspect containers, handle port conflicts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lsof/ss | System tools | Port conflict detection | Validate ports before starting services |
| pg_isready | PostgreSQL client | Database health checking | Verify Postgres accepts connections |
| curl | System tool | API health checking | Verify Ollama API responds on port 11434 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Docker Compose | Custom docker run commands | Compose provides health checks, networking, and volume management out of the box |
| Bash | Python setup script | Bash is universal, no Python needed before Python dependencies installed |
| Custom wait loops | docker compose up --wait | Built-in --wait is more reliable and handles edge cases |

**Installation:**
No installation needed - all tools are system dependencies that the script should check for.

## Architecture Patterns

### Recommended Script Structure

```bash
#!/usr/bin/env bash

# 1. Strict error handling
set -euo pipefail

# 2. Cleanup trap
trap cleanup_on_exit EXIT
trap 'echo "Interrupted"; exit 130' INT TERM

# 3. Functions
check_docker()         # Verify Docker daemon running
check_port()           # Detect port conflicts
start_postgres()       # Start PostgreSQL container
wait_for_postgres()    # Use docker compose up --wait
setup_ollama()         # Start Ollama, pull model
install_dependencies() # UV sync
index_codebase()       # Run cocosearch index
show_next_steps()      # Print usage instructions
cleanup_on_exit()      # Prompt to keep/remove containers on failure

# 4. Main flow
main() {
    check_docker
    check_port 5432 "PostgreSQL"
    check_port 11434 "Ollama"
    start_postgres
    setup_ollama
    install_dependencies
    index_codebase
    show_next_steps
}

main
```

### Pattern 1: Strict Error Handling

**What:** Set bash options to fail fast and propagate errors
**When to use:** Always, at the start of every setup script
**Example:**
```bash
# Source: https://www.namehero.com/blog/how-to-use-set-e-o-pipefail-in-bash-and-why/
#!/usr/bin/env bash
set -euo pipefail

# set -e: Exit immediately if any command fails
# set -u: Treat unset variables as errors
# set -o pipefail: Fail if any command in a pipeline fails (not just the last one)
```

### Pattern 2: Idempotent Operations

**What:** Check state before acting, use safe flags on commands
**When to use:** Every operation that modifies system state
**Example:**
```bash
# Source: https://arslan.io/2019/07/03/how-to-write-idempotent-bash-scripts/

# Safe directory creation
mkdir -p /path/to/dir  # Won't fail if exists

# Check before expensive operations
if ! docker volume inspect postgres_data &>/dev/null; then
    docker volume create postgres_data
fi

# Check if container running before starting
if ! docker ps --format '{{.Names}}' | grep -q "^cocosearch-db$"; then
    docker compose up -d db
fi

# Use force flags for overwrites
ln -sf source target  # Overwrites existing symlink safely
```

### Pattern 3: Docker Compose with Health Checks

**What:** Use built-in --wait flag instead of custom wait loops
**When to use:** Waiting for services to be ready
**Example:**
```bash
# Source: https://docs.docker.com/compose/how-tos/startup-order/

# Start and wait for healthy
docker compose up -d --wait

# Equivalent to:
# 1. Start containers
# 2. Check health checks defined in compose file
# 3. Wait until all have service_healthy condition
# 4. Return control to script

# Health check in docker-compose.yml:
# services:
#   db:
#     healthcheck:
#       test: ["CMD-SHELL", "pg_isready -U cocoindex -d cocoindex"]
#       interval: 10s
#       timeout: 5s
#       retries: 5
#       start_period: 30s
```

### Pattern 4: Cleanup Trap Handlers

**What:** Register cleanup function to run on script exit
**When to use:** Always, to handle failures gracefully
**Example:**
```bash
# Source: https://www.putorius.net/using-trap-to-exit-bash-scripts-cleanly.html

CLEANUP_NEEDED=false

cleanup_on_exit() {
    exit_code=$?

    # Only prompt if script failed and containers were started
    if [[ $exit_code -ne 0 ]] && [[ "$CLEANUP_NEEDED" == "true" ]]; then
        echo ""
        read -p "Keep containers for debugging? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cleaning up containers..."
            docker compose down
        fi
    fi
}

trap cleanup_on_exit EXIT
trap 'echo "Script interrupted"; exit 130' INT TERM

# Set flag after starting containers
docker compose up -d
CLEANUP_NEEDED=true
```

### Pattern 5: Port Conflict Detection

**What:** Check if required ports are available before starting services
**When to use:** Before docker compose up
**Example:**
```bash
# Source: https://www.cyberciti.biz/faq/unix-linux-check-if-port-is-in-use-command/

check_port() {
    local port=$1
    local service=$2

    # Use lsof on macOS/Linux (cross-platform)
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Error: Port $port is already in use (required for $service)"
        echo "Process using port $port:"
        lsof -Pi :$port -sTCP:LISTEN
        exit 1
    fi
}

check_port 5432 "PostgreSQL"
check_port 11434 "Ollama"
```

### Pattern 6: Docker Daemon Check

**What:** Verify Docker is installed and running before proceeding
**When to use:** First check in script
**Example:**
```bash
# Source: https://medium.com/@valkyrie_be/quicktip-a-universal-way-to-check-if-docker-is-running-ffa6567f8426

check_docker() {
    # Check if docker command exists
    if ! command -v docker &>/dev/null; then
        echo "Error: Docker is not installed"
        echo "Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check if daemon is running (works on macOS and Linux)
    if ! docker info &>/dev/null; then
        echo "Error: Docker daemon is not running"
        echo "Start Docker Desktop (macOS) or 'systemctl start docker' (Linux)"
        exit 1
    fi
}
```

### Pattern 7: UV Package Installation

**What:** Use UV to sync project dependencies
**When to use:** After containers are ready, before running cocosearch
**Example:**
```bash
# Source: https://docs.astral.sh/uv/

install_dependencies() {
    echo "dependencies: Installing Python packages with UV..."

    # Check if uv is installed
    if ! command -v uv &>/dev/null; then
        echo "Error: UV is not installed"
        echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Sync dependencies (idempotent, creates venv if needed)
    uv sync

    # Alternatively, if just installing without lockfile:
    # uv pip install -e .
}
```

### Pattern 8: Ollama Model Management

**What:** Check if model exists before pulling
**When to use:** After Ollama container starts
**Example:**
```bash
# Source: https://collabnix.com/setting-up-ollama-models-with-docker-compose-a-step-by-step-guide/

setup_ollama() {
    echo "ollama: Starting container..."
    # Ollama service should be in docker-compose.yml
    docker compose up -d ollama

    echo "ollama: Waiting for API to be ready..."
    timeout 60 bash -c 'until curl -s http://localhost:11434/api/tags >/dev/null; do sleep 2; done'

    echo "ollama: Checking for nomic-embed-text model..."
    if ! docker exec ollama ollama list | grep -q "nomic-embed-text"; then
        echo "ollama: Pulling nomic-embed-text (this may take a few minutes)..."
        docker exec ollama ollama pull nomic-embed-text
    else
        echo "ollama: nomic-embed-text already available"
    fi
}
```

### Pattern 9: Progress Output (Plain Text)

**What:** Inline prefix format with streamed output from tools
**When to use:** All output (per CONTEXT.md decision)
**Example:**
```bash
# Per CONTEXT.md: Plain text, no colors, inline prefix format

echo "postgres: Starting container..."
docker compose up -d db 2>&1 | sed 's/^/  /'  # Indent output

echo "postgres: Waiting for healthy status..."
docker compose up -d --wait db

echo "ollama: Pulling model..."
docker exec ollama ollama pull nomic-embed-text 2>&1 | sed 's/^/  /'

# Stream output from underlying tools (don't buffer)
echo "cocosearch: Indexing codebase..."
uv run cocosearch index .
```

### Anti-Patterns to Avoid

- **Don't use `set -e` alone:** Must combine with `set -u` and `set -o pipefail` for robust error handling
- **Don't write custom wait loops:** Use `docker compose up --wait` instead of polling in bash
- **Don't ignore cleanup:** Always use trap handlers for cleanup on exit
- **Don't assume tools exist:** Check for docker, uv, docker compose before using
- **Don't hardcode paths:** Use relative paths or derive from script location
- **Don't use colors when context says no colors:** Follow the CONTEXT.md decision

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Waiting for Docker containers | Custom sleep loops or polling | `docker compose up --wait` with health checks | Built-in flag handles retries, timeouts, and edge cases |
| Yes/No prompts | Raw read with validation loops | `read -p "prompt [y/N] " -n 1 -r; [[ $REPLY =~ ^[Yy]$ ]]` | Standard pattern, case-insensitive, handles edge cases |
| Port availability checking | Custom netcat scripts | `lsof -Pi :PORT -sTCP:LISTEN -t` | Cross-platform, works on macOS and Linux |
| Virtual environment management | Manual venv creation and activation | `uv sync` or `uv run` | UV handles venv creation, activation, and dependencies |
| Docker daemon status | Parsing ps output | `docker info &>/dev/null` | Official way, handles all edge cases |
| Model existence checking | Parsing docker exec output | `docker exec ollama ollama list | grep -q "model-name"` | Ollama's built-in list command |

**Key insight:** Setup scripts have well-established patterns. Don't reinvent docker wait logic, error handling, or cleanup mechanisms. Use bash strict mode, docker compose features, and standard CLI tools.

## Common Pitfalls

### Pitfall 1: Silent Failures in Pipelines

**What goes wrong:** Script continues after a command in a pipeline fails
**Why it happens:** By default, bash only checks the exit code of the last command in a pipeline
**How to avoid:** Use `set -o pipefail` at script start
**Warning signs:** Commands in middle of pipeline fail but script continues

### Pitfall 2: Race Conditions with Container Startup

**What goes wrong:** Script tries to use service before it's ready to accept connections
**Why it happens:** Container running != service ready. PostgreSQL takes time to initialize, Ollama needs to load
**How to avoid:** Use health checks in docker-compose.yml and `docker compose up --wait`
**Warning signs:** Intermittent connection errors, especially on slower machines

### Pitfall 3: Non-Idempotent Operations

**What goes wrong:** Running script twice fails or creates duplicate resources
**Why it happens:** Commands assume clean state (mkdir, docker volume create, etc.)
**How to avoid:** Check state before acting, use safe flags (`mkdir -p`, `docker volume inspect || create`)
**Warning signs:** Script works first time, fails on second run

### Pitfall 4: Missing Cleanup on Failure

**What goes wrong:** Failed setup leaves containers running, consuming ports and resources
**Why it happens:** No trap handler to catch exit signals
**How to avoid:** Register cleanup function with `trap cleanup_on_exit EXIT`
**Warning signs:** Port conflicts on subsequent runs after failures

### Pitfall 5: Unclear Error Messages

**What goes wrong:** Script fails with cryptic error, user doesn't know how to fix
**Why it happens:** Relying on tool's error messages without adding context
**How to avoid:** Check preconditions explicitly, provide actionable error messages
**Warning signs:** Users ask "what does this error mean?" repeatedly

### Pitfall 6: Not Streaming Tool Output

**What goes wrong:** Long operations appear hung, user kills script thinking it's stuck
**Why it happens:** Buffering output from docker pull, model download, etc.
**How to avoid:** Stream output directly, don't capture it unless necessary
**Warning signs:** Users report script "hanging" during model download

### Pitfall 7: Hardcoded Container Names Conflicts

**What goes wrong:** Container name already exists from previous run or different project
**Why it happens:** docker-compose.yml specifies `container_name` without checking
**How to avoid:** Either let Docker generate names or check if name exists before starting
**Warning signs:** "Conflict. The container name... is already in use" errors

## Code Examples

Verified patterns from official sources:

### Check Docker Daemon Running

```bash
# Source: https://medium.com/@valkyrie_be/quicktip-a-universal-way-to-check-if-docker-is-running-ffa6567f8426
check_docker() {
    if ! command -v docker &>/dev/null; then
        echo "Error: Docker is not installed"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        echo "Error: Docker daemon is not running"
        exit 1
    fi
}
```

### Wait for PostgreSQL with Docker Compose

```bash
# Source: https://docs.docker.com/compose/how-tos/startup-order/
echo "postgres: Starting container..."
docker compose up -d --wait db

# This waits for health check to pass:
# healthcheck:
#   test: ["CMD-SHELL", "pg_isready -U cocoindex -d cocoindex"]
#   interval: 10s
#   timeout: 5s
#   retries: 5
```

### Check Port Availability

```bash
# Source: https://www.cyberciti.biz/faq/unix-linux-check-if-port-is-in-use-command/
check_port() {
    local port=$1
    local service=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Error: Port $port is already in use (required for $service)"
        lsof -Pi :$port -sTCP:LISTEN
        exit 1
    fi
}
```

### Yes/No Prompt with Cleanup

```bash
# Source: https://www.shellhacks.com/yes-no-bash-script-prompt-confirmation/
read -p "Keep containers for debugging? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    docker compose down
fi
```

### UV Dependency Installation

```bash
# Source: https://docs.astral.sh/uv/
echo "dependencies: Installing Python packages with UV..."

# Sync creates venv if needed, installs all dependencies
uv sync

# Or run commands directly without activating venv
uv run cocosearch index .
```

### Ollama Model Pull (Idempotent)

```bash
# Source: https://collabnix.com/setting-up-ollama-models-with-docker-compose-a-step-by-step-guide/
MODEL="nomic-embed-text"

if ! docker exec ollama ollama list | grep -q "$MODEL"; then
    echo "ollama: Pulling $MODEL model..."
    docker exec ollama ollama pull "$MODEL"
else
    echo "ollama: $MODEL already available"
fi
```

### Trap Handler with Cleanup

```bash
# Source: https://www.putorius.net/using-trap-to-exit-bash-scripts-cleanly.html
CLEANUP_NEEDED=false

cleanup_on_exit() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]] && [[ "$CLEANUP_NEEDED" == "true" ]]; then
        echo ""
        read -p "Keep containers for debugging? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            docker compose down
        fi
    fi
}

trap cleanup_on_exit EXIT
trap 'echo "Interrupted"; exit 130' INT TERM
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom wait scripts (wait-for-it.sh) | `docker compose up --wait` | Docker Compose v2 (2020+) | Eliminates need for third-party scripts |
| Colored output with escape codes | Plain text, grep-friendly | Modern CI/CD (2020+) | Scripts work in CI without terminal emulation |
| pip + virtualenv manual | UV package manager | 2024 | 10-100x faster, automatic venv management |
| netstat for port checking | lsof / ss commands | 2015+ | netstat deprecated, lsof works cross-platform |
| Docker Compose v1 (docker-compose) | Docker Compose v2 (docker compose) | 2022 | Native Docker CLI integration, better performance |

**Deprecated/outdated:**
- **wait-for-it.sh:** Third-party script for waiting on services - replaced by `docker compose up --wait`
- **netstat:** Deprecated in favor of `ss` on Linux, `lsof` for cross-platform
- **docker-compose (hyphenated):** v1 syntax, replaced by `docker compose` (space) in v2
- **Manual virtualenv activation:** UV handles this automatically with `uv run`

## Open Questions

Things that couldn't be fully resolved:

1. **Ollama health check reliability**
   - What we know: Can check API with curl, can list models with `ollama list`
   - What's unclear: Best way to define health check in docker-compose.yml for Ollama
   - Recommendation: Use curl to /api/tags endpoint as health check, proven pattern

2. **Cross-platform compatibility (macOS vs Linux)**
   - What we know: Docker Desktop works differently than Docker Engine, lsof available on both
   - What's unclear: Whether Docker daemon check works identically on both platforms
   - Recommendation: Test on both platforms, `docker info` is documented to work universally

3. **UV not installed scenario**
   - What we know: UV can be installed with curl script
   - What's unclear: Should script auto-install UV or require it as precondition?
   - Recommendation: Check for UV, fail with install instructions (don't auto-install)

## Sources

### Primary (HIGH confidence)

- [Docker Compose Startup Order - Official Docs](https://docs.docker.com/compose/how-tos/startup-order/) - Health checks and depends_on patterns
- [Ollama Docker Documentation - Official](https://docs.ollama.com/docker) - Docker setup and model pulling
- [UV Documentation - Official](https://docs.astral.sh/uv/) - Package manager usage and commands
- [Docker Compose Health Checks - Last9](https://last9.io/blog/docker-compose-health-checks/) - Comprehensive guide to health check configuration
- [Ollama Docker Hub Page - Official](https://hub.docker.com/r/ollama/ollama) - Container image documentation

### Secondary (MEDIUM confidence)

- [How to Write Idempotent Bash Scripts - Arslan.io](https://arslan.io/2019/07/03/how-to-write-idempotent-bash-scripts/) - Idempotent patterns
- [Set -e -o pipefail Explanation - GitHub Gist](https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425) - Bash strict mode
- [Bash Trap Command - Putorius](https://www.putorius.net/using-trap-to-exit-bash-scripts-cleanly.html) - Cleanup patterns
- [Check Port Use in Linux - NixCraft](https://www.cyberciti.biz/faq/unix-linux-check-if-port-is-in-use-command/) - Port detection methods
- [Check Docker Daemon Running - Medium](https://medium.com/@valkyrie_be/quicktip-a-universal-way-to-check-if-docker-is-running-ffa6567f8426) - Docker daemon checks
- [Yes/No Bash Prompts - ShellHacks](https://www.shellhacks.com/yes-no-bash-script-prompt-confirmation/) - User input patterns

### Tertiary (LOW confidence)

None - all critical findings verified with official documentation or established community sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official docs for Docker Compose, UV, Ollama verified
- Architecture: HIGH - Patterns verified with official Docker docs and established bash practices
- Pitfalls: HIGH - Based on documented common issues and official recommendations

**Research date:** 2026-01-31
**Valid until:** 2026-03-31 (60 days - stable domain, slow-moving standards)
