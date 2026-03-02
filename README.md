# kioku-lite

> Personal memory engine for AI agents. Tri-hybrid search, zero Docker, single SQLite file.

[![PyPI](https://img.shields.io/pypi/v/kioku-lite)](https://pypi.org/project/kioku-lite/)
[![Python](https://img.shields.io/pypi/pyversions/kioku-lite)](https://pypi.org/project/kioku-lite/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**kioku-lite** (*kioku = memory in Japanese*) gives AI agents long-term memory with causal reasoning. It stores, indexes, and retrieves personal memories using tri-hybrid search (BM25 + Vector + Knowledge Graph) — all within a single SQLite file.

**[Homepage](https://phuc-nt.github.io/kioku-lite-landing/)** · **[Docs](https://phuc-nt.github.io/kioku-lite-landing/blog.html)** · **[Blog (EN)](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro)** · **[Blog (JA)](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro-ja)** · **[Blog (VN)](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro-vn)** · **[PyPI](https://pypi.org/project/kioku-lite/)**

---

## Why kioku-lite

Most agent memory systems store flat text or vectors. They can't answer *"Why was I stressed last month?"* because they don't track how events, emotions, and decisions connect. kioku-lite solves this with a Knowledge Graph on top of traditional search — and it runs 100% local with no LLM calls.

## Features

- **Tri-hybrid search** — BM25 (FTS5) + Vector (sqlite-vec) + Knowledge Graph
- **Zero infrastructure** — no Docker, no ChromaDB, no external servers
- **Fully offline** — FastEmbed ONNX embedding, no API keys needed
- **Agent-driven KG** — agent extracts entities and indexes them (no built-in LLM)
- **CLI + Python API** — works with any agent that runs shell commands
- **Built-in personas** — companion (emotion tracking) and mentor (decision tracking)
- **Multilingual** — 100+ languages via multilingual-e5-large

## Install

```bash
pipx install "kioku-lite[cli]"        # recommended
# or
pip install "kioku-lite[cli]"
```

## Quick start

```bash
# Save a memory
kioku-lite save "Had coffee with Alice. Discussed the Kioku project." --mood work

# Search (tri-hybrid: BM25 + vector + KG)
kioku-lite search "What has Alice been up to?"

# Index knowledge graph (agent provides extracted entities)
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Alice","type":"PERSON"}]' \
  --relationships '[{"source":"Alice","rel_type":"WORKS_ON","target":"Kioku"}]'

# Recall everything about an entity
kioku-lite recall "Alice"
```

<details>
<summary>Python API</summary>

```python
from kioku_lite.service import KiokuLiteService

svc = KiokuLiteService()
result = svc.save_memory("Met Alice at the café.", mood="happy")
results = svc.search_memories("Who did I meet?", limit=5)
```

</details>

## Agent integration

kioku-lite works with any AI agent that can run CLI commands. Setup guides:

- **[Claude Code / Cursor / Windsurf](https://phuc-nt.github.io/kioku-lite-landing/agent-setup.html)** — copy-paste the guide, agent does the rest
- **[OpenClaw](https://phuc-nt.github.io/kioku-lite-landing/openclaw-setup.html)** — auto-generates SOUL.md + TOOLS.md

```bash
kioku-lite install-profile companion   # emotion tracking persona
kioku-lite install-profile mentor      # decision tracking persona
```

## Architecture

```
Agent (Claude Code, Cursor, …)
  │
  ├─ save "..."          ──→  SQLite FTS5 + sqlite-vec + Markdown backup
  ├─ kg-index <hash>     ──→  GraphStore (nodes, edges, aliases)
  └─ search "..."        ──→  BM25 ∪ Vector ∪ KG → RRF rerank
```

> kioku-lite **never calls an LLM**. The agent extracts entities from its own context, keeping the memory engine 100% local and LLM-agnostic.

Deep dive: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) · [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) · [Search Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture)

## Benchmark

vs [kioku-agent-kit](https://github.com/phuc-nt/kioku-agent-kit) (full Docker stack):

| Metric | Docker stack | kioku-lite |
|---|---|---|
| Search latency | ~2-3s | **~1.2s** |
| Precision@3 | 0.60 | **0.60** |
| Infrastructure | 3 containers | **zero** |

kioku-lite targets **personal use and single-agent** setups. kioku-agent-kit targets **enterprise multi-tenant** deployments.

## Configuration

All settings via `KIOKU_LITE_` env vars or `.env` file:

| Variable | Default | Description |
|---|---|---|
| `KIOKU_LITE_USER_ID` | `default` | User ID for data isolation |
| `KIOKU_LITE_DATA_DIR` | `~/.kioku-lite/data` | SQLite DB location |
| `KIOKU_LITE_MEMORY_DIR` | `~/.kioku-lite/memory` | Markdown backup location |
| `KIOKU_LITE_EMBED_MODEL` | `intfloat/multilingual-e5-large` | Embedding model |

## Development

```bash
git clone https://github.com/phuc-nt/kioku-agent-kit-lite
cd kioku-agent-kit-lite
pip install -e ".[cli,dev]"
pytest
```

## License

[MIT](LICENSE) © 2026 Phuc Nguyen
