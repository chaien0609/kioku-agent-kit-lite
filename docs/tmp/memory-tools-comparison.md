# Kioku Lite vs Mem0 vs NeuralMemory — A Practical Comparison

> **Summary:** Three very different philosophies for giving AI agents persistent memory. Mem0 bets on managed cloud infrastructure. NeuralMemory reimagines retrieval as a brain-inspired spreading activation network. Kioku Lite bets on the opposite extreme: everything in one SQLite file, no server, no LLM, no cloud.

---

## At a Glance

| | **Kioku Lite** | **Mem0** | **NeuralMemory** |
|---|---|---|---|
| **Core model** | Tri-hybrid search (BM25 + Vector + KG) | Vector search + Graph memory | Spreading activation (neuron/synapse graph) |
| **Storage** | Single SQLite file | Managed cloud (vector store + graph) | SQLite or FalkorDB |
| **LLM required** | ❌ Never | ✅ Always (OpenAI by default) | Optional (embeddings + LLM for enrichment) |
| **Offline-first** | ✅ Fully offline | ❌ Cloud-dependent | ✅ Can run offline |
| **Docker required** | ❌ Zero | ❌ Zero (managed SaaS) | ❌ Zero |
| **Entity graph** | ✅ Open-schema, agent-driven | ✅ Managed graph service | ✅ 24 synapse types |
| **Setup** | `pipx install` + 2 commands | `pip install` + API key | `pip install` + optional server |
| **Target** | Personal / local-first | Enterprise / production SaaS | Developer / feature-complete |
| **Pricing** | MIT, free | Open-source core + paid platform | MIT, free |
| **MCP tools** | Via CLI + SKILL.md | SDK-based | 28 dedicated MCP tools |

---

## Mem0

### What it is

[Mem0](https://mem0.ai) (pronounced "mem-zero") is a **managed memory layer** for AI applications. It positions itself as enterprise infrastructure: SOC 2 compliant, HIPAA-ready, with a hosted platform that runs the vector store, graph services, and rerankers on your behalf.

The open-source core (`pip install mem0ai`) exists, but the primary value proposition is the **Mem0 platform** — a cloud service where you point your agent at an API endpoint and memories are handled for you.

### Architecture

```
Your Agent
    │
    └─ mem0 SDK call
           │
           ▼
    Mem0 Platform (cloud)
    ├── LLM (gpt-4.1-nano by default)   ← extracts & compresses memories
    ├── Vector store                     ← semantic retrieval
    ├── Graph service (Mem0g)            ← entity relationships
    └── Reranker                         ← relevance scoring
```

Memory is **multi-level**: user-level (persistent across all sessions), session-level (conversation-specific), and agent state.

### Memory model

When a conversation turn arrives, Mem0:
1. Calls an LLM to **extract salient information** from the text
2. **Deduplicates and compresses** against existing memories
3. Stores the result in the vector store (+ graph if enabled)
4. On retrieval, performs semantic search and optionally graph traversal

The result: **90% token reduction** vs full-context approaches, **26% accuracy gain** vs OpenAI's native memory (per their research paper).

### Strengths

- **Zero infra management** — the platform handles vector DB, graph DB, rerankers
- **Production-grade** — SOC 2, HIPAA, versioned memories, audit trail
- **Multi-level hierarchy** — user/session/agent memory scopes
- **Strong benchmarks** — documented accuracy and latency improvements
- **SDK breadth** — Python, JavaScript, LangGraph, CrewAI integrations

### Limitations

- **Always-online** — no offline operation; all memory calls go to the cloud
- **LLM required** — every `add()` call triggers an LLM to extract memories (cost + latency)
- **Vendor dependency** — the managed platform is proprietary; self-hosting loses most managed features
- **Not personal-scale** — pricing and architecture target teams and production apps, not individual developers
- **Data privacy** — memories leave your machine

---

## NeuralMemory

### What it is

[NeuralMemory](https://github.com/nhadaututtheky/neural-memory) (`pip install neural-memory`) is an ambitious **brain-inspired memory system** that abandons the "database search" metaphor entirely. Instead of querying a vector index, it stores memories as neurons with typed synaptic connections and retrieves them through **spreading activation** — propagating signals through the graph until relevant memories "surface" by association.

### Architecture

```
Query
  │
  ▼
Decompose → extract time hints, entities, intent
  │
  ▼
Find Anchors → locate starting neurons in graph
  │
  ▼
Spread Activation → signal propagates through synapses (with decay)
  │
  ▼
Intersection → identify high-activation subgraph
  │
  ▼
Extract Context → generate coherent response
```

The building blocks:

| Concept | Description |
|---|---|
| **Neuron** | A single memory unit (concept, entity, action, time, state) |
| **Synapse** | Typed, weighted connection between neurons (e.g., `CAUSED_BY`, `LEADS_TO`, `RESOLVED_BY`) |
| **Fiber** | An ordered sequence of neurons forming a coherent experience |
| **Spreading activation** | Signal propagates from anchor neurons outward with distance-based decay |

**11 memory types**: Fact, Decision, Preference, Todo, Insight, Context, Instruction, Error, Workflow, Reference
**24 synapse types**: CAUSED_BY, LEADS_TO, RESOLVED_BY, CONTRADICTS, SUPPORTS, DEPENDS_ON, ...

### Feature depth

NeuralMemory ships with an unusually large feature surface:

- **28 MCP tools** — remember, recall, context, todo, auto-capture, suggestions, session tracking, narratives, health checks, conflict resolution, versioning, sync, imports
- **Knowledge Base training** — ingest PDF, DOCX, PPTX, HTML, JSON, XLSX, CSV, MD; trained memories are permanently pinned
- **Ebbinghaus forgetting curve** — memories decay over time; spaced repetition (Leitner system) for review
- **Brain health diagnostics** — purity scoring, conflict detection
- **Version control** — snapshots and rollback
- **Multi-device sync** — push/pull between instances
- **Brain transplant** — migrate memories between agents
- **Codebase indexing** — code-aware memories
- **Imports** — migrate from ChromaDB, Mem0, Cognee, Graphiti, LlamaIndex
- **VS Code extension** — tree view, graph explorer, CodeLens
- **React dashboard** — 7-page UI (Overview, Health, Graph, Timeline, Evolution, Diagrams, Settings)
- **Vietnamese NLP** — `neural-memory[nlp-vi]` optional package

### Strengths

- **Novel retrieval model** — spreading activation can surface non-obvious connections that pure vector search misses
- **Richest feature set** in the space (28 MCP tools, dashboard, forgetting curve, versioning)
- **Offline-capable** — fully local when embeddings are disabled or using local models
- **Import existing data** — migrate from other memory systems
- **Developer tooling** — VS Code extension + React dashboard
- **Vietnamese language support** — purpose-built

### Limitations

- **High complexity** — Schema v20, 24 synapse types, 11 memory types; significant learning curve
- **Embeddings optional but impactful** — without them, anchor finding degrades substantially
- **Early stage** — ~70 GitHub stars, rapid schema evolution (v20 implies many breaking changes)
- **No single-file simplicity** — SQLite or FalkorDB, optional FastAPI server
- **Spreading activation latency** — signal propagation through a large graph is slower than a direct BM25/vector lookup

---

## Kioku Lite

### What it is

[Kioku Lite](https://phuc-nt.github.io/kioku-lite-landing/) (`pip install kioku-lite`) is a **local-first, single-file memory engine** that takes the opposite bet from Mem0: no cloud, no LLM, no external server. Everything runs in one SQLite file using standard extensions.

The core insight: **the agent already has an LLM** (Claude, GPT, Gemini, or a local model). There is no need to pay for a second LLM call just to store a memory. Let the agent extract entities in its own context, then call `kioku-lite` to index and persist them.

### Architecture

```
Agent (Claude Code, Cursor, …)
  │
  ├─ kioku-lite save "..."          ──→  memories (FTS5)      BM25 keyword search
  │                                  ──→  memory_vec           Vector similarity (FastEmbed ONNX)
  │                                  ──→  memories/YYYY-MM.md  Markdown backup
  │
  ├─ kioku-lite kg-index <hash>     ──→  kg_nodes / kg_edges   Knowledge Graph (BFS traversal)
  │
  └─ kioku-lite search "..."        ──→  BM25 ∪ Vector ∪ KG → RRF rerank → top-N
```

Three search signals fused via **Reciprocal Rank Fusion (RRF)**:

| Signal | Tech | What it finds |
|---|---|---|
| BM25 | SQLite FTS5 | Exact keyword matches, names, dates |
| Vector | sqlite-vec + FastEmbed ONNX (multilingual-e5-large) | Semantically similar memories |
| Knowledge Graph | SQLite graph store (BFS) | Entity-linked memories, causal chains |

The KG uses an **open schema** — entity types and relationship types are plain strings. The agent can create `EMOTION`, `DECISION`, `PROJECT`, or any custom type at will.

### Strengths

- **Zero infrastructure** — no Docker, no server, no API key; a single `.sqlite` file
- **No LLM cost** — kioku-lite never calls an LLM; the agent provides entity extraction in its own context
- **Fully offline** — FastEmbed ONNX runs locally; after the one-time model download (~1.1GB), zero network needed
- **Tri-hybrid recall** — three signals fused means fewer missed memories vs any single-method system
- **Open-schema KG** — add any entity type or relationship type on the fly
- **Human-readable backup** — every memory is also a Markdown file, git-trackable
- **Built-in personas** — `companion` (emotion + life events) and `mentor` (decisions + lessons) ship out of the box
- **Multilingual** — multilingual-e5-large supports 100+ languages natively
- **Minimal install** — `pipx install "kioku-lite[cli]"` + 2 commands, agent is memory-enabled

### Limitations

- **Agent cooperation required** — agent must explicitly call `save` + `kg-index`; there is no auto-capture
- **KG quality depends on agent** — if the agent extracts poor entities, the graph is poor
- **Cold start** — first query takes ~5s for FastEmbed model warm-up
- **Personal scale** — designed for 1 user / 1 agent; not multi-tenant
- **No dashboard** — inspection is via CLI or markdown files

---

## Philosophy Comparison

| Dimension | Kioku Lite | Mem0 | NeuralMemory |
|---|---|---|---|
| **Memory metaphor** | A searchable personal journal | A managed enterprise database | A living brain |
| **Who calls the LLM** | The agent (already has one) | Mem0 platform (adds cost) | Optional (user controls) |
| **Infrastructure bet** | SQLite is enough | Cloud infra is necessary | SQLite or graph DB |
| **Retrieval model** | Hybrid search → RRF fusion | Vector search + graph traversal | Spreading activation |
| **Complexity tradeoff** | Simple, explicit, predictable | Simple API, complex internals | Powerful, complex to debug |
| **Privacy** | 100% on-device | Data leaves device | 100% on-device |
| **Right scale** | Personal (1 user, 1+ agents) | Production apps, teams | Individual developers |

---

## Feature Matrix

| Feature | Kioku Lite | Mem0 | NeuralMemory |
|---|---|---|---|
| **BM25 keyword search** | ✅ FTS5 | ❌ | ❌ |
| **Vector / semantic search** | ✅ FastEmbed ONNX (local) | ✅ (cloud-managed) | ✅ optional (local or API) |
| **Knowledge Graph** | ✅ open-schema, BFS | ✅ managed graph (Mem0g) | ✅ 24 synapse types |
| **Fused ranking (RRF)** | ✅ | ✅ reranker (cloud) | ❌ (activation score) |
| **Entity recall** | ✅ `recall "entity"` | ✅ | ✅ via anchor activation |
| **Causal chains** | ✅ KG traversal | ✅ (limited) | ✅ CAUSED_BY, LEADS_TO, ... |
| **Timeline view** | ✅ `timeline` | ✅ (platform) | ✅ timeline narrative |
| **Memory decay / forgetting curve** | ❌ | ❌ | ✅ Ebbinghaus model |
| **Spaced repetition** | ❌ | ❌ | ✅ Leitner system |
| **Multi-device sync** | ❌ | ✅ (platform) | ✅ push/pull |
| **Human-readable backup** | ✅ Markdown files | ❌ | ❌ |
| **Git-trackable** | ✅ | ❌ | ❌ |
| **Offline-first** | ✅ | ❌ | ✅ |
| **Zero LLM dependency** | ✅ | ❌ (always LLM) | ✅ (optional) |
| **MCP integration** | ✅ via SKILL.md / CLI | ✅ SDK | ✅ 28 dedicated tools |
| **Dashboard UI** | ❌ | ✅ (platform) | ✅ React (7 pages) |
| **VS Code extension** | ❌ | ❌ | ✅ |
| **Document ingestion (PDF, DOCX…)** | ❌ | ❌ | ✅ |
| **Import from other tools** | ❌ | ❌ | ✅ (Mem0, ChromaDB, ...) |
| **Built-in personas** | ✅ companion + mentor | ❌ | ❌ |
| **Profile isolation** | ✅ per-profile directory | ✅ per-user/session/agent | ✅ per-brain |
| **Open-source** | ✅ MIT | ✅ core (Apache 2.0) | ✅ MIT |
| **Self-hosted** | ✅ (it's just a file) | ✅ (OSS, loses managed features) | ✅ |

---

## Setup Complexity

### Kioku Lite

```bash
pipx install "kioku-lite[cli]"
kioku-lite setup            # download embedding model (~1.1GB, one-time)
kioku-lite init --global    # inject SKILL.md into agent
```

Your agent can now call `kioku-lite save`, `kioku-lite search`, and `kioku-lite kg-index`. No configuration file, no API key, no running service.

### Mem0

```python
pip install mem0ai

from mem0 import MemoryClient
client = MemoryClient(api_key="your-key")  # cloud; or configure self-hosted vector DB

client.add("I prefer dark mode", user_id="alice")
results = client.search("UI preferences", user_id="alice")
```

Self-hosted requires configuring a compatible vector store (Qdrant, Pinecone, Chroma, etc.) and an LLM provider.

### NeuralMemory

```bash
pip install "neural-memory[all]"   # full install with server + embeddings + extraction

nmem remember "..."
nmem recall "..."
nmem serve                         # start optional FastAPI + React dashboard
```

Full functionality also requires configuring embedding providers (sentence-transformers locally, or Google Gemini / OpenAI API for richer extraction).

---

## When to Use What

| Scenario | Best fit | Why |
|---|---|---|
| Personal daily journal / life memory with a coding agent | **Kioku Lite** | Zero infra, offline, KG for causal queries, built-in personas |
| Production chatbot with millions of users | **Mem0** | Managed infra, SOC 2, multi-tenant, latency benchmarks |
| Developer wanting maximum feature depth | **NeuralMemory** | 28 MCP tools, forgetting curve, versioning, dashboard |
| Tracking decisions + causal chains | **Kioku Lite** or **NeuralMemory** | Both have explicit relationship types; Kioku Lite is simpler |
| Enterprise / team deployment | **Mem0** | Cloud platform, compliance, audit trail |
| Air-gapped / offline environment | **Kioku Lite** or **NeuralMemory** | Both run 100% local |
| Migrating from another memory system | **NeuralMemory** | Built-in importers for Mem0, ChromaDB, Cognee, etc. |
| Multilingual personal memory | **Kioku Lite** | multilingual-e5-large, 100+ languages |
| Codebase-aware memory | **NeuralMemory** | Codebase indexing built in |

### Complementary use

These tools are not mutually exclusive:

- **Kioku Lite + Mem0:** Use Kioku Lite for your personal agent's local memory, Mem0 for a multi-user production service.
- **Kioku Lite + NeuralMemory:** Kioku Lite's simplicity for daily save/search, NeuralMemory for deeper knowledge base training from documents.

---

## Summary

**Mem0** is the right choice if you're building a production application and want managed infrastructure, compliance guarantees, and don't mind the LLM overhead per memory operation.

**NeuralMemory** is the right choice if you want maximum feature depth, enjoy building on a brain-inspired model, and need capabilities like document ingestion, forgetting curves, and a visual dashboard.

**Kioku Lite** is the right choice if you want to give **your personal agent** long-term memory right now, with zero infra overhead, full offline capability, and a Knowledge Graph that traces causes and effects — all in a single SQLite file.

> Kioku Lite doesn't try to replace Mem0 or NeuralMemory. It occupies a specific niche: **personal, local-first, LLM-agnostic memory for individual developers and their agents.**

---

## Related docs

- [01-system.md](../architecture/01-system.md) — Kioku Lite system architecture
- [03-search.md](../architecture/03-search.md) — Search pipeline (BM25 + Vector + KG → RRF)
- [04-kg-open-schema.md](../architecture/04-kg-open-schema.md) — Open-schema entity and relationship types
- [05-memory-comparison.md](../architecture/05-memory-comparison.md) — Kioku Lite vs Claude Code vs OpenClaw
