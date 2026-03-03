# Kioku Lite vs Mem0

> **One-line contrast:** Mem0 is managed cloud infrastructure for production apps. Kioku Lite is a local-first memory engine built around the agent you already have.

---

## Infrastructure

**Mem0** runs your memory on the cloud. The platform manages the vector store, graph services, and rerankers. You point your app at an API endpoint — no provisioning, but your data leaves your machine and you depend on network availability.

**Kioku Lite** stores everything in a single SQLite file on your device. No server, no Docker, no external database. The entire memory engine — BM25 index, vector store, knowledge graph — lives in one file at `~/.kioku-lite/`.

---

## LLM usage

This is where the philosophies diverge most sharply.

**Mem0** calls an LLM on every `add()` operation to extract and compress memories. This is automatic and invisible, but it means every memory write has an LLM cost — latency, API spend, and a dependency on an external service.

**Kioku Lite never calls an LLM.** It doesn't need to — the agent *is* the LLM. When Claude Code, Cursor, or any other agent saves a memory, it already understands the context. It extracts entities and relationships in its own reasoning step, then calls `kioku-lite kg-index` to index them. The memory engine only stores and retrieves.

This is **agent-driven architecture**: the intelligence stays in the agent where it belongs. Kioku Lite stays lean, offline, and LLM-agnostic.

---

## Offline

**Mem0** requires a network connection. Memory reads and writes go to the Mem0 platform (or a self-hosted vector DB you maintain separately).

**Kioku Lite** is fully offline after a one-time model download (~1.1GB for the FastEmbed ONNX embedding model). Once set up, zero network calls — ever.

---

## Search

**Mem0** uses vector search as the primary retrieval method, with graph traversal as an optional add-on (Mem0g).

**Kioku Lite** uses **tri-hybrid search** — three signals fused via Reciprocal Rank Fusion:

| Signal | What it finds |
|---|---|
| **BM25 (FTS5)** | Exact keyword matches — names, dates, technical terms |
| **Vector (sqlite-vec + FastEmbed)** | Semantically similar memories — paraphrases, related topics |
| **Knowledge Graph (BFS traversal)** | Entity-linked memories — causal chains, relationships across time |

No single search method catches everything. BM25 fails on paraphrases. Vector search fails on rare keywords. Graph traversal only works on indexed entities. Fusing all three gives more complete recall than any one approach alone.

---

## Quick comparison

| | Kioku Lite | Mem0 |
|---|---|---|
| **Infrastructure** | Single SQLite file | Managed cloud (vector store + graph + reranker) |
| **LLM calls** | Zero (agent-driven) | Every memory write |
| **Offline** | ✅ Fully local | ❌ Cloud-dependent |
| **Search** | BM25 + Vector + KG → RRF | Vector + optional graph |
| **Privacy** | 100% on-device | Data sent to cloud |
| **Target scale** | Personal (1 user, 1+ agents) | Production apps, multi-tenant |
| **Setup** | `pipx install` + 2 commands | API key + vector DB config |
| **License** | MIT | Apache 2.0 (core) + paid platform |

---

## What about kioku-full?

The roadmap includes **kioku-full** — a version closer to Mem0 in scale: dedicated vector DB, dedicated graph DB, multi-tenant, API-accessible. Suitable for team and enterprise deployments.

But even kioku-full will keep two core differences:

1. **Agent-driven** — no built-in LLM extraction. The calling agent provides entity and relationship data. Memory stays a storage and retrieval engine, not an opinionated transformer of your data.
2. **Tri-hybrid search** — BM25 + Vector + KG fused via RRF, not vector-primary with graph as an afterthought.

---

## Related

- [Architecture overview](../architecture/01-system.md)
- [Search pipeline](../architecture/03-search.md)
- [Memory tools comparison (3-way)](./memory-tools-comparison.md)
