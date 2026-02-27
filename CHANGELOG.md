# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-02-27

### Added
- Initial release of kioku-agent-kit-lite
- Tri-hybrid search: BM25 (SQLite FTS5) + Vector (sqlite-vec) + Knowledge Graph
- FastEmbed ONNX embedder — local, offline-capable (`intfloat/multilingual-e5-large`)
- OllamaEmbedder — HTTP-based for dev/benchmark comparison
- CLI commands: `save`, `search`, `kg-index`, `show`, `delete`, `list`, `stats`
- Agent-driven KG indexing via `kg-index` command
- Multi-user support via `KIOKU_LITE_USER_ID`
- SQLite-based graph store (BFS traversal, entity aliases)
- Markdown file storage (human-readable backup)
- Comprehensive test suite — 5 modules, 149+ tests
- Architecture documentation and benchmark results
- PyPI-ready packaging via Hatchling

### Architecture decisions
- Zero Docker — all storage in a single SQLite file
- Agent-driven KG: kioku-lite stores what the agent provides, no built-in LLM calls
- Embedding default: `intfloat/multilingual-e5-large` (1024-dim, multilingual)
- E5 instruction format: `passage:` for indexing, `query:` for search

### Benchmark (vs kioku-agent-kit full Docker)
- Search latency: 1.2s vs 2-3s (kioku-lite **1.7-7.6× faster**)
- Precision@3: 0.60 = 0.60 (equal quality with same KG extraction)
- Infrastructure: pip install vs 3 Docker containers
