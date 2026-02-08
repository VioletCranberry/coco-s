# CocoSearch

Hybrid search for codebases -- semantic understanding meets keyword precision. Everything runs locally.

Powered by [CocoIndex](https://github.com/cocoindex-io/cocoindex) data transformation framework for AI.

## Quick Start

**1. Start infrastructure**

```bash
docker compose up -d
```

**2. Index your project**

```bash
uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch index .
```

**3. Register with your AI assistant**

```bash
claude mcp add --scope user cocosearch -- \
  uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch mcp --project-from-cwd
```

No environment variables needed -- defaults match Docker credentials.

## Features

- **Hybrid search** -- semantic similarity + keyword matching via RRF fusion.
- **Symbol filtering** -- filter by function, class, method, or symbol name patterns.
- **Context expansion** -- smart expansion to enclosing function/class boundaries.
- **Query caching** -- exact and semantic cache for fast repeated queries.
- **Index observability** -- stats dashboard for monitoring index health.
- **Parse health tracking** -- detect and report parsing issues across indexed files.
- **Stay private** -- everything runs locally, no external API calls.
- **Use with AI assistants** -- integrate via CLI or MCP ([Claude Code](https://claude.com/product/claude-code), [Claude Desktop](https://claude.com/download), [OpenCode](https://opencode.ai/)).

## Supported Languages

```bash
uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch languages
```

CocoSearch indexes 31 programming languages via Tree-sitter. Symbol extraction (for `--symbol-type` and `--symbol-name` filtering) is available for 10 languages.

- **Full Support (Symbol-Aware)**: Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, Ruby, PHP. All features: hybrid search, symbol filtering, smart context expansion. Symbol types extracted: `function`, `class`, `method`, `interface`.
- **Basic Support**: C#, CSS, Fortran, HTML, JSON, Kotlin, Markdown, Pascal, R, Scala, Shell, Solidity, SQL, Swift, TOML, XML, YAML, Bash, Dockerfile, HCL, and more. Features: hybrid search, semantic + keyword search.

## Components

- **Ollama** -- runs the embedding model (`nomic-embed-text`) locally.
- **PostgreSQL + pgvector** -- stores code chunks and their vector embeddings for similarity search.
- **CocoSearch** -- CLI and MCP server that coordinates indexing and search.

## Setup

### Docker Compose (Recommended)

```bash
docker compose up -d
```

This starts two containers:

- **PostgreSQL 17** with pgvector on port `5432` (credentials: `cocosearch`/`cocosearch`)
- **Ollama** with `nomic-embed-text` on port `11434`

CocoSearch runs natively on your machine -- Docker only provides the infrastructure services.

### Manual Setup (Alternative)

If you prefer to manage services yourself, you need:

- PostgreSQL with the pgvector extension, accessible on port `5432`
- Ollama with the `nomic-embed-text` model pulled, accessible on port `11434`

## Using CocoSearch

### MCP Registration (Recommended)

Register CocoSearch once and it works across all your projects. The `--project-from-cwd` flag detects which project you are working in automatically.

**Claude Code:**

```bash
claude mcp add --scope user cocosearch -- \
  uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch mcp --project-from-cwd
```

Claude Code supports MCP Roots, so project detection is fully automatic. For Claude Desktop, OpenCode, and other configuration options, see [MCP Configuration](./docs/mcp-configuration.md).

### CLI

```bash
# Index a project
uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch index /path/to/project

# Search with natural language
uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch search "authentication flow" --pretty

# View index stats with parse health
uvx --from git+https://github.com/VioletCranberry/coco-s cocosearch stats --pretty
```

For the full list of commands and flags, see [CLI Reference](./docs/cli-reference.md).

## Configuration

Create `.cocosearch.yaml` in your project root to customize indexing:

```yaml
indexing:
  # See also https://cocoindex.io/docs/ops/functions#supported-languages
  include_patterns:
    - "*.py"
    - "*.js"
    - "*.ts"
    - "*.go"
    - "*.rs"
  exclude_patterns:
    - "*_test.go"
    - "*.min.js"
  chunk_size: 1000 # bytes
  chunk_overlap: 300 # bytes
```

## Documentation

- [Architecture Overview](./docs/architecture.md)
- [MCP Configuration](./docs/mcp-configuration.md)
- [MCP Tools Reference](./docs/mcp-tools.md)
- [CLI Reference](./docs/cli-reference.md)
- [Retrieval Logic](./docs/retrieval.md)
- [Search Features](./docs/search-features.md)
- [Dogfooding](./docs/dogfooding.md)

## Skills

CocoSearch ships with three skills for Claude Code:

- **coco-debugging** ([SKILL.md](./skills/coco-debugging/SKILL.md)) -- use when debugging an error, unexpected behavior, or tracing how code flows through a system. Guides root cause analysis using CocoSearch semantic and symbol search.
- **coco-onboarding** ([SKILL.md](./skills/coco-onboarding/SKILL.md)) -- use when onboarding to a new or unfamiliar codebase. Guides you through understanding architecture, key modules, and code patterns step-by-step using CocoSearch.
- **coco-refactoring** ([SKILL.md](./skills/coco-refactoring/SKILL.md)) -- use when planning a refactoring, extracting code into a new module, renaming across the codebase, or splitting a large file. Guides impact analysis and safe step-by-step execution using CocoSearch.

See [Extend Claude with skills](https://code.claude.com/docs/en/skills) for how to install and use them.

## Disclaimer

This is a personal initiative built using [GSD](https://github.com/glittercowboy/get-shit-done), with careful manual refinements. It was designed as a local-first, private solution to accelerate self-onboarding and explore spec-driven development.
