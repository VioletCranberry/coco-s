# Contributing to CocoSearch

Contributions are welcome! Whether it's a bug fix, a new language handler, improved search logic, or better documentation — all help is appreciated.

## Code of Conduct

- Be respectful and constructive in all interactions.
- Welcome newcomers and help them get oriented.
- Focus feedback on the code, not the person.
- Assume good intent; ask before criticizing.

## Development Setup

**Prerequisites:** Docker, [uv](https://github.com/astral-sh/uv) (Python package manager), Python >= 3.11.

```bash
# Start infrastructure (PostgreSQL 17 + pgvector, Ollama)
docker compose up -d

# Install dependencies
uv sync

# Index the codebase (verifies everything works end-to-end)
uv run cocosearch index .
```

PostgreSQL runs on port 5432, Ollama on port 11434. Defaults require no `.env` file.

## Process

1. **Open an issue first** for non-trivial changes — bug reports, feature proposals, or refactoring ideas. This avoids duplicate work and lets us discuss the approach before you invest time.
2. **Fork and branch.** Create a feature branch from `main` with a descriptive name.
3. **Keep PRs focused.** One concern per pull request. Smaller PRs are easier to review and merge.
4. **Write descriptive commit messages.** No strict format required — just explain what changed and why.
5. **Submit a PR against `main`.** Include a clear description of the change and link to the related issue if one exists.

## Code Quality

**Linting and formatting** are handled by [Ruff](https://github.com/astral-sh/ruff):

```bash
uv run ruff check src/ tests/       # Lint
uv run ruff check --fix src/ tests/  # Auto-fix lint issues
uv run ruff format src/ tests/       # Format
```

**Testing** uses [pytest](https://docs.pytest.org/). All tests are unit tests, fully mocked, and require no infrastructure:

```bash
uv run pytest                                    # Run all tests
uv run pytest tests/unit/handlers/ -v            # Handler tests
uv run pytest tests/unit/search/test_cache.py -v # Single file
uv run pytest -k "test_name" -v                  # Single test by name
```

Before submitting a PR:
- Run `uv run ruff check src/ tests/` and fix any issues.
- Run `uv run ruff format src/ tests/`.
- Run `uv run pytest` and ensure all tests pass.

**Async tests** use `pytest-asyncio` in strict mode — async test functions must be decorated with `@pytest.mark.asyncio`.

## Contribution Areas

### Adding Language Support

CocoSearch has three independent systems for language support — a language can use any combination:

- **Language handlers** — custom chunking for languages not in CocoIndex's built-in Tree-sitter list.
- **Symbol extraction** — Tree-sitter query-based extraction for `--symbol-type`/`--symbol-name` filtering.
- **Grammar handlers** — domain-specific chunking within a base language (e.g., GitHub Actions within YAML).

See [Adding Languages](./docs/adding-languages.md) for the full guide, templates, and registration checklist.

### Other Areas

- **Search improvements** — ranking, caching, context expansion, query analysis.
- **CLI features** — new subcommands, output formats, flags.
- **MCP tools** — new tools or improvements to the MCP server and web dashboard.
- **Documentation** — fixes, clarifications, examples.

## Project Structure

```
src/cocosearch/
  cli.py              # CLI entry point (argparse)
  mcp/                # MCP server (FastMCP) + web dashboard
  indexer/             # CocoIndex pipeline, Tree-sitter symbols, embeddings
    queries/           # .scm files for symbol extraction (14 languages)
  search/              # Hybrid search engine (RRF, cache, context expansion)
  config/              # YAML config with 4-level precedence
  handlers/            # Language-specific chunking (HCL, Bash, Dockerfile, etc.)
    grammars/          # Grammar handlers (GitHub Actions, GitLab CI, etc.)
  management/          # Index lifecycle (discovery, stats, clearing)
  dashboard/           # Terminal (Rich) and web (Chart.js) dashboards
tests/unit/            # All tests — fully mocked, no infra needed
```

For a deeper dive, see [Architecture Overview](./docs/architecture.md).
