# kioku-lite

> Personal memory engine for AI agents. Tri-hybrid search, zero Docker, single SQLite file.

[![PyPI](https://img.shields.io/pypi/v/kioku-lite)](https://pypi.org/project/kioku-lite/)
[![Python](https://img.shields.io/pypi/pyversions/kioku-lite)](https://pypi.org/project/kioku-lite/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**kioku-lite** — *kioku* (記憶) means "memory" in Japanese: 記 (ki) to record, 憶 (oku) to remember. A lightweight, fully local memory engine that gives AI agents long-term memory with causal reasoning, using tri-hybrid search (BM25 + Vector + Knowledge Graph) in a single SQLite file.

**[Homepage](https://phuc-nt.github.io/kioku-lite-landing/)** · **[Docs](https://phuc-nt.github.io/kioku-lite-landing/blog.html)** · **[The Story](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro)** · **[PyPI](https://pypi.org/project/kioku-lite/)**

> **Read the intro:** [Why I built a Knowledge Graph memory engine for my AI agents](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro) — also in [日本語](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro-ja) and [Tiếng Việt](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro-vn)

---

## Why kioku-lite

Most agent memory systems store flat text or vectors. They can't answer *"Why was I stressed last month?"* because they don't track how events, emotions, and decisions connect. kioku-lite solves this with a Knowledge Graph on top of traditional search — running 100% local with no LLM calls.

## Features

- **Tri-hybrid search** — BM25 (FTS5) + Vector (sqlite-vec) + Knowledge Graph
- **Zero infrastructure** — no Docker, no ChromaDB, no external servers
- **Fully offline** — FastEmbed ONNX embedding, no API keys needed
- **Agent-driven KG** — agent extracts entities and indexes them (no built-in LLM)
- **CLI + Python API** — works with any agent that runs shell commands
- **Built-in personas** — companion (emotion tracking) and mentor (decision tracking)
- **Multilingual** — 100+ languages via multilingual-e5-large

## Getting started

Install and connect to your agent in 3 commands:

```bash
pipx install "kioku-lite[cli]"
kioku-lite init --global
kioku-lite install-profile companion
```

That's it. Your agent now has long-term memory with Knowledge Graph.

Full setup guides for each agent type:
- **[Claude Code / Cursor / Windsurf](https://phuc-nt.github.io/kioku-lite-landing/agent-setup.html)** — copy-paste the guide, agent does the rest
- **[OpenClaw](https://phuc-nt.github.io/kioku-lite-landing/openclaw-setup.html)** — auto-generates SOUL.md + TOOLS.md

## Architecture

```
Agent (Claude Code, Cursor, …)
  │
  ├─ save "..."          ──→  SQLite FTS5 + sqlite-vec + Markdown backup
  ├─ kg-index <hash>     ──→  GraphStore (nodes, edges, aliases)
  └─ search "..."        ──→  BM25 ∪ Vector ∪ KG → RRF rerank
```

> kioku-lite **never calls an LLM**. The agent extracts entities from its own context, keeping the memory engine 100% local and LLM-agnostic.

Deep dive: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) · [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) · [Search Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture) · [KG Open Schema](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kg-open-schema)

## Development

```bash
git clone https://github.com/phuc-nt/kioku-agent-kit-lite
cd kioku-agent-kit-lite
pip install -e ".[cli,dev]"
pytest
```

## License

[MIT](LICENSE) © 2026 Phuc Nguyen
