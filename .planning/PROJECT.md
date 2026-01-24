# CocoSearch

## What This Is

A local-first code and documentation indexer exposed via MCP. Point it at a codebase, it indexes using CocoIndex with Ollama embeddings and PostgreSQL storage, then search semantically through an MCP interface. Built for understanding unfamiliar codebases without sending code to external services.

## Core Value

Semantic code search that runs entirely locally — no data leaves your machine.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Index a codebase directory under a named index
- [ ] Search a named index with natural language, return relevant code chunks
- [ ] Clear a specific named index
- [ ] Support multiple named indexes simultaneously
- [ ] Run PostgreSQL via Docker for vector storage
- [ ] Use Ollama for local embeddings
- [ ] Expose functionality via MCP server

### Out of Scope

- Answer synthesis inside MCP — Claude (the caller) handles synthesis from returned chunks
- Cloud storage or external embedding APIs — this is local-first
- Real-time file watching / auto-reindex — manual index trigger only for v1
- Web UI — MCP interface only

## Context

- CocoIndex library (https://github.com/cocoindex-io/cocoindex) provides the indexing foundation
- UV for Python package management
- Primary use case: onboarding to unfamiliar codebases
- Mostly indexing code, occasionally documentation

## Constraints

- **Runtime**: PostgreSQL in Docker, Ollama running locally
- **Package manager**: UV (not pip)
- **Interface**: MCP server (no CLI, no web UI)
- **Privacy**: All processing local — no external API calls for embeddings or storage

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CocoIndex as indexing engine | User-specified, designed for this use case | — Pending |
| Ollama for embeddings | Local-first requirement, no external APIs | — Pending |
| PostgreSQL in Docker | Vector storage, easy local setup | — Pending |
| MCP returns chunks only | Simpler architecture, calling LLM synthesizes | — Pending |
| Named indexes | Support multiple codebases without conflicts | — Pending |

---
*Last updated: 2025-01-24 after initialization*
