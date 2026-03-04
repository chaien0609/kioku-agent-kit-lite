# From CLI to Server: Kioku Architecture & the Road to kioku-server

*Published: 2026-03-04 · v0.1.28*

Hey builders!

This post covers two things that came up repeatedly after the [kioku-lite intro](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro): how the architecture works in practice, and where the project is heading with kioku-server. Plus a comparison with Anthropic's official MCP Memory Server.

---

## Part 1 — kioku-lite in Brief

kioku-lite stores everything in a **single SQLite file** — no Docker, no external servers. The interface is a **CLI + SKILL.md**: any agent that can run shell commands reads the skill file and gains instant memory capabilities.

The core is a **tri-hybrid search** pipeline fusing three signals via RRF (Reciprocal Rank Fusion):

| Signal | Tech | Finds |
|---|---|---|
| BM25 | SQLite FTS5 | Exact keywords, names, dates |
| Vector | sqlite-vec + FastEmbed ONNX | Semantically similar memories |
| Knowledge Graph | SQLite BFS | Entity-linked memories, causal chains |

Writes use a two-step agent protocol: `save` (text → SHA256 hash + embedding + FTS5 row) then `kg-index` (agent extracts entities → GraphStore). **No built-in LLM** — the calling agent is already an LLM.

Graph search improvements in v0.1.27–0.1.28: self-entity exclusion (hub node filtered from BFS seeds), adaptive hop limit (degree > 15 → 1 hop), and multi-entity intersection (results reachable from *all* seed entities).

*→ Full details: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) · [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) · [Search Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture)*

---

## Part 2 — kioku-server: The Roadmap

### Same core logic, different infrastructure

kioku-lite proved the algorithms work. kioku-server takes the same core — tri-hybrid search, RRF fusion, agent-driven KG, open schema — and swaps the infrastructure for enterprise deployment:

```
kioku-lite                        kioku-server (planned)
─────────────────────────         ────────────────────────────────
Interface: CLI + SKILL.md    →    Interface: MCP Server
Embedding: FastEmbed ONNX    →    Embedding: Ollama / cloud API
Vector DB: sqlite-vec         →    Vector DB: ChromaDB (dedicated)
Graph DB:  SQLite tables      →    Graph DB:  FalkorDB (Cypher)
Scale:     1 user, local      →    Scale:     multi-tenant, cloud
```

The service layer (`KiokuService`) remains the same. The algorithms remain the same. Only the I/O adapters change.

### Architecture: kioku-server

```
┌───────────────────────────────────────────────────────────────┐
│                   MCP SERVER LAYER                            │
│   MCP tools: memory/save, memory/search, memory/kg-index,    │
│              memory/recall, memory/connect, memory/entities   │
└──────────────────────────┬────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              KiokuService  (shared core logic)               │
│   save_memory() │ search() │ kg_index() │ recall()           │
└──────┬───────────────────┬─────────────────────┬─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
  PostgreSQL /         Embedder              Dedicated DBs
  Object Storage       Ollama / API  ┌──────────────────────────┐
  (memory records,     (or local     │  ChromaDB                │
  Markdown export)     ONNX)         │  (vector store)          │
                                     │                          │
                                     │  FalkorDB                │
                                     │  (property graph,        │
                                     │   Cypher queries)        │
                                     └──────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Multi-Tenant Isolation                          │
│  API key → namespace → per-tenant data isolation            │
│  (same pattern as multi-user profiles in kioku-lite)         │
└──────────────────────────────────────────────────────────────┘
```

### What changes vs kioku-lite

| Dimension | kioku-lite | kioku-server |
|---|---|---|
| **Interface** | CLI + SKILL.md | MCP Server (JSON-RPC) |
| **Embedding** | FastEmbed ONNX (local) | Ollama / cloud API (configurable) |
| **Vector store** | sqlite-vec (in-process) | ChromaDB (dedicated container) |
| **Graph store** | SQLite tables + BFS | FalkorDB (property graph, Cypher) |
| **Scale** | 1 user, personal machine | Multi-tenant, cloud-deployable |
| **Auth** | Profile switching (`users --use`) | API keys per tenant |
| **Deployment** | `pipx install` | Docker Compose / Kubernetes |

### What stays the same

- **Core algorithms**: tri-hybrid search, RRF fusion, self-entity exclusion, adaptive hops, multi-entity intersection
- **Knowledge graph schema**: open-schema entity types, relationship types, evidence fields
- **Agent-driven KG**: no built-in LLM extraction — the agent still does it
- **Content hash**: SHA256 dedup key linking memories across all storage layers
- **Multi-profile support**: same isolation concept, implemented via API namespaces

### Why MCP interface for the server?

The agent ecosystem is converging on MCP (Model Context Protocol) as the standard for tool integration. For a personal CLI tool, SKILL.md is simpler — no background process, just shell commands. For an enterprise server serving multiple agents and users, MCP is the natural fit:

- Standard tool discovery protocol
- Works with Claude Desktop, Cline, Cursor, and any MCP-compatible client
- Server handles auth, rate limiting, tenant isolation
- Agents don't need to install anything — just point at the server endpoint

---

## Part 3 — Comparison: vs Anthropic's MCP Memory Server

Anthropic ships an [official MCP Memory Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) as a reference implementation in the MCP servers repository. Since both kioku-server and the MCP Memory Server provide memory via MCP tools, it's worth comparing them directly.

### What is the MCP Memory Server?

The MCP Memory Server is a **TypeScript reference implementation** that gives agents a simple knowledge graph stored in a JSONL flat file. It exposes 6 MCP tools:

- `create_entities` — add entity nodes
- `create_relations` — add typed relations between entities
- `add_observations` — attach facts to entities
- `delete_entities` / `delete_relations` / `delete_observations`
- `search_nodes` — find entities by name (string match)
- `read_graph` — return the entire graph

The storage is a `.jsonl` file where each line is a JSON object representing an entity or relation. Every `search_nodes` call filters that list by string match.

### Architecture contrast

```
MCP Memory Server                    kioku-server (planned)
─────────────────────────            ──────────────────────────────
Storage: JSONL flat file             Storage: ChromaDB + FalkorDB
Search:  String match only           Search:  Tri-hybrid (BM25 + vector + KG)
Embedding: None                      Embedding: Ollama / cloud API
Graph:   Flat entity list            Graph:   Property graph (Cypher)
Scale:   Single user, local file     Scale:   Multi-tenant, cloud
Language: TypeScript                 Language: Python
Interface: 6 MCP tools               Interface: MCP tools (same protocol)
```

### Feature comparison

| Feature | MCP Memory Server | kioku-lite | kioku-server (planned) |
|---|---|---|---|
| **Storage** | JSONL flat file | Single SQLite file | ChromaDB + FalkorDB + PostgreSQL |
| **BM25 keyword search** | ❌ | ✅ (SQLite FTS5) | ✅ |
| **Semantic / vector search** | ❌ | ✅ (FastEmbed ONNX) | ✅ (cloud-scale) |
| **Knowledge Graph traversal** | ❌ (flat list, no BFS) | ✅ (BFS, adaptive hops) | ✅ (FalkorDB Cypher) |
| **Fused ranking (RRF)** | ❌ | ✅ | ✅ |
| **Entity recall** | Partial (list filter) | ✅ `recall "entity"` | ✅ |
| **Causal chains / paths** | ❌ | ✅ `connect "A" "B"` | ✅ |
| **Timeline / temporal queries** | ❌ | ✅ `--from --to` | ✅ |
| **Multi-entity intersection** | ❌ | ✅ (v0.1.28) | ✅ |
| **Hub node exclusion** | ❌ | ✅ (v0.1.27) | ✅ |
| **Multi-tenant** | ❌ | ❌ (profile-based) | ✅ |
| **Multilingual** | ❌ | ✅ (100+ languages) | ✅ |
| **Offline capable** | ✅ | ✅ | Configurable |
| **Human-readable backup** | ❌ | ✅ Markdown | ✅ Markdown export |
| **Production-ready** | ❌ (reference impl) | For personal use | Yes |
| **Language** | TypeScript | Python | Python |

### Philosophy: reference vs production

The MCP Memory Server is **intentionally simple**. It's a reference implementation showing developers how to build memory tools with MCP — a starting point, not an endpoint. Anthropic ships it as a template to fork and adapt.

kioku-lite and kioku-server are production-grade tools built for real agents doing real work:

> **MCP Memory Server**: "Here's how memory tools could work. Extend this."
>
> **kioku-lite**: "Memories stored in SQLite with real semantic search, graph traversal, and temporal queries. Ready now, personal scale."
>
> **kioku-server**: "Same algorithms, enterprise infrastructure. Team memory, multi-tenant cloud."

### Practical difference: search quality

The clearest gap is search quality. Given 50 memories about daily life:

| Query | MCP Memory Server | kioku-lite |
|---|---|---|
| "stressed about the project" | Returns entities named "stress" or "project" | Returns semantically similar memories (vector) + entity-linked memories (KG) |
| Memories about Alice | Finds "Alice" entity node | Traverses all edges from Alice node (BFS), fused with semantic matches |
| "what caused my anxiety last month" | No temporal filter, no causal traversal | `--from 2026-02-01 --to 2026-02-28` + KG paths `TRIGGERED_BY` |
| Memories linking Alice and Project X | No graph traversal | `connect "Alice" "Project X"` returns relationship path |

---

## Summary

```
kioku-lite (now)       kioku-server (planned)    MCP Memory Server
────────────────       ──────────────────────    ─────────────────
Personal scale         Enterprise / Cloud        Reference impl
CLI interface          MCP interface             MCP interface
SQLite-everything      Independent DBs           JSONL flat file
Tri-hybrid search      Tri-hybrid + cloud DBs    String match only
Agent-driven KG        Agent-driven KG           Agent-driven KG
0 Docker               Docker Compose / K8s      0 infrastructure
v0.1.28 · available    In development            Available (TypeScript)
```

**Use kioku-lite if:** You want personal long-term memory for your coding/journaling agent, right now, zero infra, offline-capable.

**Use kioku-server if:** You're building a multi-agent system or enterprise deployment where multiple users share a memory backend. (Not yet available — in development.)

**Use MCP Memory Server if:** You want a simple starting point to understand how MCP memory tools work, or you want to build your own custom memory layer.

---

- GitHub: [github.com/phuc-nt/kioku-agent-kit-lite](https://github.com/phuc-nt/kioku-agent-kit-lite)
- Homepage: [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)
- Changelog: [CHANGELOG.md](https://github.com/phuc-nt/kioku-agent-kit-lite/blob/main/CHANGELOG.md)

Thanks for reading! If this helped clarify the architecture, a ⭐ on GitHub goes a long way.
