# System Architecture — kioku-agent-kit-lite

> Last updated: 2026-03-02 (v0.1.18)

## Overview

kioku-agent-kit-lite là personal memory engine cho AI agents với thiết kế **zero-dependency**: không cần Docker, không cần server bên ngoài. Mọi storage đều trong một file SQLite duy nhất, embedding chạy local bằng ONNX.

**Triết lý thiết kế:**
- **Agent-driven KG** — kioku-lite không tự gọi LLM. Agent tự extract entities → gọi `kg-index` để lưu vào graph.
- **SQLite-everything** — BM25 (FTS5) + vector (sqlite-vec) + knowledge graph đều trong một file `.db`.
- **Offline-capable** — FastEmbed ONNX chạy không cần internet sau khi model đã download.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     INTERFACE LAYER                          │
│                                                              │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  cli.py  (Typer CLI)                                  │  │
│   │  • save       • kg-index    • kg-alias               │  │
│   │  • search     • recall      • connect                │  │
│   │  • entities   • timeline    • users    • setup       │  │
│   │  • init       • install-profile                      │  │
│   └──────────────────────────┬────────────────────────────┘  │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               KiokuLiteService  (service.py)                 │
│   save_memory() │ search() │ kg_index() │ delete_memory()   │
└────────┬─────────────────┬─────────────────────┬─────────────┘
         │                 │                     │
         ▼                 ▼                     ▼
  MarkdownStore        Embedder              KiokuDB
  ~/memory/*.md       FastEmbed             (single .db)
  (human backup)      ONNX local    ┌────────────────────────┐
                                    │  SQLiteStore           │
                                    │  ├── memories (FTS5)   │
                                    │  └── memory_vec        │
                                    │      (sqlite-vec)      │
                                    │                        │
                                    │  GraphStore            │
                                    │  ├── kg_nodes          │
                                    │  ├── kg_edges          │
                                    │  └── kg_aliases        │
                                    └────────────────────────┘
```

## Module Structure

```
src/kioku_lite/
├── __init__.py
├── config.py          # Settings (Pydantic) — env vars KIOKU_LITE_*
├── service.py         # KiokuLiteService — tất cả business logic
├── cli.py             # CLI (Typer) — 12 commands
│
├── pipeline/          # WRITE path
│   ├── db.py          # KiokuDB — facade cho SQLiteStore + GraphStore
│   ├── sqlite_store.py # FTS5 (BM25) + sqlite-vec (vector) tables
│   ├── graph_store.py  # SQLite KG: entities, relations, aliases
│   └── embedder.py    # FastEmbedder (ONNX) | OllamaEmbedder | FakeEmbedder
│
├── search/            # READ path
│   ├── bm25.py        # BM25 keyword search (SQLite FTS5)
│   ├── semantic.py    # Vector similarity (sqlite-vec ANN)
│   ├── graph.py       # Graph traversal (SQLite BFS)
│   └── reranker.py    # Reciprocal Rank Fusion (RRF)
│
└── storage/
    └── markdown.py    # Markdown file I/O (source of truth)
```

## Data Flow: Save

See [02-write-save-kg-index.md](02-write-save-kg-index.md) for full details.

| Step | Component | Output |
|---|---|---|
| 1 | SHA256(text) | `content_hash` — universal dedup key |
| 2 | Embedder.embed("passage: " + text) | 1024-dim vector |
| 3a | MarkdownStore | `~/memory/YYYY-MM/hash.md` |
| 3b | SQLiteStore.upsert_memory | FTS5 indexed row |
| 3c | SQLiteStore.upsert_vector | sqlite-vec row |
| 4 | *(Agent calls kg-index separately)* | entities + relations in GraphStore |

## Data Flow: Search

See [03-search.md](03-search.md) for full details.

| Step | Component | Output |
|---|---|---|
| 1 | Embedder.embed("query: " + text) | 1024-dim query vector |
| 2a | BM25Search | top-K BM25 results |
| 2b | SemanticSearch | top-K cosine similarity results |
| 2c | GraphSearch | entity-linked memories |
| 3 | RRF Reranker | fused, deduplicated top-N |

## Data Flow: KG Index (Agent-Driven)

See [02-write-save-kg-index.md](02-write-save-kg-index.md) for full details.

```
Agent extracts from context:
  entities     → [{"name": "Hùng", "type": "PERSON"}, ...]
  relationships → [{"source": "Hùng", "rel_type": "WORKS_ON", "target": "Kioku"}]
        ↓
  kioku-lite kg-index <hash> --entities '...' --relationships '...'
        ↓
  GraphStore.upsert_entities() → kg_entities
  GraphStore.upsert_relations() → kg_relations
  GraphStore.add_alias()        → kg_aliases
```

## Configuration

All settings via environment variables with prefix `KIOKU_LITE_`:

| Variable | Default | Purpose |
|---|---|---|
| `KIOKU_LITE_USER_ID` | `default` | User isolation |
| `KIOKU_LITE_DATA_DIR` | `~/.kioku-lite/data` | SQLite DB location |
| `KIOKU_LITE_MEMORY_DIR` | `~/.kioku-lite/memory` | Markdown files |
| `KIOKU_LITE_EMBED_PROVIDER` | `fastembed` | `fastembed` \| `ollama` \| `fake` |
| `KIOKU_LITE_EMBED_MODEL` | `intfloat/multilingual-e5-large` | Model name |
| `KIOKU_LITE_EMBED_DIM` | `1024` | Embedding dimensions |
| `KIOKU_LITE_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama URL (nếu dùng) |

## Multi-User Isolation

```
~/.kioku-lite/
├── users/
│   ├── default/
│   │   ├── data/kioku.db     ← SQLite (FTS5 + vec + KG)
│   │   └── memory/           ← Markdown files
│   │       └── 2026-02/
│   │           └── abc123.md
│   └── phuc/
│       ├── data/kioku.db
│       └── memory/
└── ...
```

## Graceful Degradation

| Component Down | Impact |
|---|---|
| Embedder / FastEmbed | Vector indexing skipped. BM25 + KG still work. |
| sqlite-vec extension | Vector search skipped. BM25 + KG still work. |
| GraphStore | KG search skipped. BM25 + Vector still work. |
| SQLite | ❌ Critical — tất cả search fail |

## Comparison với kioku-agent-kit (full)

| | kioku-agent-kit-lite | kioku-agent-kit |
|---|---|---|
| **Vector store** | sqlite-vec (in-process) | ChromaDB (Docker :8001) |
| **Graph store** | SQLite BFS | FalkorDB (Docker :6381) |
| **Embedding** | FastEmbed ONNX (local) | Ollama (Docker :11434) |
| **KG extraction** | Agent-driven (no built-in LLM) | Claude Haiku (built-in) |
| **Search latency** | ~1.2s | ~2–3s (normal), up to 9s (throttled) |
| **Setup** | `pip install kioku-agent-kit-lite` | Docker Compose |
| **Offline capability** | ✅ (embed only) | ❌ (needs Ollama + APIs) |
| **Ideal use case** | Local dev, edge, serverless | Production, team memory |
