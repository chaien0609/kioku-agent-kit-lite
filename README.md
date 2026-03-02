# kioku-lite

> Personal memory engine for AI agents — zero Docker, SQLite-everything.

[![PyPI](https://img.shields.io/pypi/v/kioku-lite)](https://pypi.org/project/kioku-lite/)
[![Python](https://img.shields.io/pypi/pyversions/kioku-lite)](https://pypi.org/project/kioku-lite/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**kioku-lite** (*kioku = memory in Japanese*) is a lightweight, fully local memory engine that gives AI agents long-term memory. It stores, indexes, and retrieves personal memories using tri-hybrid search — all within a single SQLite file, no Docker or external servers required.

🌐 **Homepage:** [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)
📦 **PyPI:** [pypi.org/project/kioku-lite](https://pypi.org/project/kioku-lite/)
📖 **Blog & Guides:** [phuc-nt.github.io/kioku-lite-landing/blog.html](https://phuc-nt.github.io/kioku-lite-landing/blog.html)

---

## Features

- ✅ **Tri-hybrid search** — BM25 (FTS5) + Vector (sqlite-vec) + Knowledge Graph (SQLite)
- ✅ **Zero Docker** — no ChromaDB, FalkorDB, or Ollama server needed
- ✅ **FastEmbed ONNX** — local embedding, offline-capable (`intfloat/multilingual-e5-large`)
- ✅ **Agent-driven KG** — agent extracts entities → `kg-index` (no built-in LLM dependency)
- ✅ **CLI** — `kioku-lite save`, `search`, `kg-index`, `recall`, `connect`, and more
- ✅ **Python API** — import `KiokuLiteService` directly into your code
- ✅ **Multilingual** — Vietnamese, English, and 100+ languages
- ✅ **Agent Profiles** — built-in personas (companion, mentor) with `install-profile`

## Installation

```bash
pip install "kioku-lite[cli]"
```

Or with [pipx](https://pipx.pypa.io/) (recommended for CLI-only use):

```bash
pipx install "kioku-lite[cli]"
```

## Quick Start

### CLI

```bash
# Save a memory
kioku-lite save "Had coffee with Alice today. Discussed the Kioku project." --mood work

# Search memories (tri-hybrid: BM25 + vector + graph)
kioku-lite search "What has Alice been up to?"

# Index knowledge graph (agent provides extracted entities)
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Alice","type":"PERSON"},{"name":"Kioku","type":"PROJECT"}]' \
  --relationships '[{"source":"Alice","rel_type":"WORKS_ON","target":"Kioku"}]'

# Recall everything about an entity
kioku-lite recall "Alice"

# Find connections between entities
kioku-lite connect "Alice" "Kioku"
```

### Python API

```python
from kioku_lite.service import KiokuLiteService

svc = KiokuLiteService()

# Save
result = svc.save_memory("Met Alice and Bob at the café.", mood="happy")
print(result["content_hash"])

# Search (BM25 + Vector + KG)
results = svc.search_memories("Who did I meet today?", limit=5)
for r in results["results"]:
    print(r["content"], r["score"])
```

## How It Works

```
┌─────────────────────────────────────────────┐
│              Agent (Claude, GPT, …)         │
│                                             │
│  1. Save memory    → kioku-lite save "..."  │
│  2. Extract entities (using agent's own LLM)│
│  3. Index KG       → kioku-lite kg-index    │
│  4. Search         → kioku-lite search "…"  │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│          KiokuLiteService                   │
│                                             │
│  MarkdownStore  → ~/memory/*.md (backup)    │
│  FastEmbed ONNX → local 1024-dim embedding  │
│  SQLite DB      → BM25 + Vector + KG       │
└─────────────────────────────────────────────┘
```

> **Design principle:** kioku-lite **never calls an LLM** — the agent is responsible for extracting entities from its own conversation context. This keeps the memory engine 100% local and LLM-agnostic.

## Agent Integration

kioku-lite works with any AI agent that can run CLI commands:

| Agent | Setup |
|---|---|
| **Claude Code** | `kioku-lite init --global` → auto-discovers skill |
| **Cursor / Windsurf** | `kioku-lite init` per project |
| **OpenClaw** | `kioku-lite install-profile <persona>` → derive SOUL.md + TOOLS.md |

Built-in personas:

```bash
kioku-lite install-profile companion   # Emotional companion
kioku-lite install-profile mentor      # Business & career mentor
```

For full setup instructions, visit the [Blog & Guides](https://phuc-nt.github.io/kioku-lite-landing/blog.html).

## Benchmark

Compared against [kioku-agent-kit](https://github.com/phuc-nt/kioku-agent-kit) (full Docker stack), using the same embedding model and Claude Haiku for KG extraction:

| Metric | kioku-agent-kit (Docker) | kioku-lite | |
|---|---|---|---|
| Search latency | ~2–3s | **~1.2s** | **lite is faster** |
| Precision@3 | 0.60 | **0.60** | **Equal** |
| Recall@5 | **1.04** | 0.89 | kit slightly better |
| Infrastructure | 3 Docker containers | **Zero** | **lite wins** |

> **Positioning:** kioku-agent-kit (full) is designed for **enterprise and multi-tenant** deployments — with Docker-based infrastructure (ChromaDB, FalkorDB, Ollama) and built-in LLM entity extraction. **kioku-lite** is designed for **personal use, edge computing, and single-agent** setups — zero infrastructure, fully local, and offline-capable. Same search quality, different scale.

## Configuration

All settings via environment variables with prefix `KIOKU_LITE_`:

| Variable | Default | Description |
|---|---|---|
| `KIOKU_LITE_USER_ID` | `default` | User ID for data isolation |
| `KIOKU_LITE_DATA_DIR` | `~/.kioku-lite/data` | SQLite DB directory |
| `KIOKU_LITE_MEMORY_DIR` | `~/.kioku-lite/memory` | Markdown backup directory |
| `KIOKU_LITE_EMBED_PROVIDER` | `fastembed` | `fastembed` \| `ollama` \| `fake` |
| `KIOKU_LITE_EMBED_MODEL` | `intfloat/multilingual-e5-large` | Embedding model name |
| `KIOKU_LITE_EMBED_DIM` | `1024` | Embedding dimensions |

Or use a `.env` file:

```env
KIOKU_LITE_USER_ID=alice
KIOKU_LITE_EMBED_PROVIDER=fastembed
```

## Development

```bash
git clone https://github.com/phuc-nt/kioku-agent-kit-lite
cd kioku-agent-kit-lite
python -m venv .venv && source .venv/bin/activate
pip install -e ".[cli,dev]"
pytest
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE) © 2026 Phúc Nguyễn
