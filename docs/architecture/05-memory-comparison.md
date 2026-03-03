# Memory Comparison — Kioku Lite vs Mem0 vs Claude Code vs OpenClaw

---

## Summary

Four different approaches to agent memory, each with a different design philosophy:

| System | Infrastructure | LLM usage | Search | Knowledge Graph | Offline |
|---|---|---|---|---|---|
| **Mem0** | Cloud-managed | Every write (extraction) | Vector + Graph | ✅ Managed | ❌ |
| **Claude Code** | Flat markdown files | None | Context window only | ❌ | ✅ |
| **OpenClaw** | SQLite per-agent | None | Semantic (embedding) | ❌ | ❌ |
| ✦ **Kioku Lite** | **Single SQLite file** | **Agent-driven (no extra call)** | **Tri-hybrid (BM25 + vector + KG)** | **✅ Agent-driven** | **✅** |

---

## Mem0 — Managed Cloud Memory

### How it works

[Mem0](https://mem0.ai) is a managed memory platform. On every `add()` call, Mem0 invokes an LLM to extract and compress memories, then stores the result in a cloud-managed vector store and optional graph service. Retrieval goes through vector search and reranking, all handled server-side.

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

Multi-level memory: user-level (persistent across sessions), session-level, and agent state.

### Characteristics

- **Cloud-managed.** The platform runs the vector store, graph service, and reranker. No provisioning needed, but data leaves your machine.
- **LLM on every write.** Entity extraction and memory compression are automatic, but each `add()` call costs an LLM round-trip.
- **Vector-primary search.** Semantic retrieval with optional graph traversal (Mem0g) as an add-on.
- **Enterprise-grade.** SOC 2, HIPAA compliant, versioned memories, audit trail, multi-tenant.

### Strengths

- Zero infra to manage — platform handles everything
- Automatic memory extraction — agent doesn't need to think about what to save
- Production-grade compliance and multi-tenancy
- Strong benchmarks: 26% accuracy gain, 91% lower latency vs full-context approaches

### Limitations

- Always-online — no offline operation
- LLM cost per write — latency and API spend on every memory addition
- Data leaves device — privacy consideration for personal use
- Vendor dependency — self-hosting loses most managed features

---

## Claude Code — File-Based Memory

### How it works

Claude Code relies on markdown files loaded into the context window at session start:

| File | Scope | Purpose |
|---|---|---|
| `CLAUDE.md` | Per-project | Developer instructions, rules, preferences |
| `MEMORY.md` | Per-project | Auto-generated learnings from past sessions |
| `~/.claude/CLAUDE.md` | Global | Cross-project preferences |

### Characteristics

- **No database.** Everything is plain text files — human-readable, git-trackable.
- **No search.** The entire file is loaded into the context window. If the file exceeds ~200 lines, content may be truncated or moved to sub-files.
- **No structured data.** No entity extraction, no relationships, no graph. Memory is unstructured prose.
- **Session boundary.** Claude Code does not persist conversational memory between sessions by default. `MEMORY.md` captures build commands and debug insights, not personal memories.

### Strengths

- Zero setup — just create a markdown file
- Human-editable — full transparency
- Version-controllable via git
- Works offline

### Limitations

- Memory capacity limited by context window
- No semantic search — can't query "what did Alice say about the project?"
- No cross-referencing between memories
- No user isolation (single CLAUDE.md per project)

---

## OpenClaw — Chunk-Based Embedding Memory

### How it works

OpenClaw maintains a per-agent SQLite database at `~/.openclaw/memory/<agent-id>.sqlite`:

```sql
-- Schema (simplified)
files     (path, source, hash, mtime, size)
chunks    (id, path, text, embedding, model, start_line, end_line)
-- FTS5 index on chunks.text
```

Each agent workspace also uses markdown files for identity:

| File | Purpose |
|---|---|
| `SOUL.md` | Agent persona and directives |
| `TOOLS.md` | Tool documentation |
| `USER.md` | Manually maintained user profile |
| `IDENTITY.md` | Agent name and display info |
| `HEARTBEAT.md` | Periodic task definitions |

### Characteristics

- **File-based chunking.** OpenClaw indexes workspace files into chunks, each with an embedding vector.
- **Semantic search.** Can find relevant chunks by embedding similarity.
- **No knowledge graph.** No entity extraction, no relationship tracking, no graph traversal.
- **Per-agent isolation.** Each agent gets its own SQLite database (typically ~68KB at baseline).
- **Compaction.** Long conversations are summarized to stay within context limits.

### Strengths

- Automatic — no manual memory management needed
- Semantic search on workspace content
- Per-agent isolation built in
- Conversation compaction prevents unlimited growth

### Limitations

- No entity linking — searching for "Alice" won't surface all memories about Alice
- No relationship graph — can't query "how is Alice connected to Project X?"
- `USER.md` is manually maintained — agent doesn't auto-populate it
- No cross-agent memory sharing
- Memory is workspace-scoped, not user-scoped

---

## Kioku Lite — Tri-Hybrid Memory Engine

### How it works

Kioku Lite uses three complementary search methods backed by a single SQLite database:

```
Agent calls CLI → KiokuLiteService → SQLite
                                     ├── memories (FTS5)     → BM25 keyword search
                                     ├── memory_vec          → Vector similarity (FastEmbed ONNX)
                                     └── kg_nodes/kg_edges   → Knowledge Graph (BFS traversal)

Results → RRF Reranker → Fused top-N
```

Additionally, every memory is persisted as a human-readable Markdown file (`~/.kioku-lite/users/<id>/memory/`).

### Characteristics

- **Agent-driven KG.** The agent extracts entities and relationships → calls `kg-index`. No built-in LLM.
- **Tri-hybrid search.** BM25 (exact keywords) + vector (semantic similarity) + KG (entity-linked memories) → fused via Reciprocal Rank Fusion.
- **Open schema.** Entity and relationship types are plain strings — no fixed enum, agent creates new types on the fly.
- **Multi-profile isolation.** Each user/persona gets an independent data directory (`~/.kioku-lite/users/<profile_id>/`).
- **Markdown backup.** Every memory has a human-readable Markdown file — inspectable, git-trackable.

### On LLM usage

Kioku Lite never calls an LLM internally. This is intentional: **the agent is already an LLM**. When Claude Code, Cursor, or any other agent saves a memory, it extracts entities and relationships in its own reasoning step, then calls `kg-index` to index them. No extra LLM call, no extra cost, no extra latency. The memory engine stays lean and LLM-agnostic.

### Strengths

- Three search signals fused → higher recall than any single method
- Knowledge graph enables `recall "Alice"`, `connect "Alice" "Project X"`, `entities`
- Agent-driven extraction works with any LLM (Claude, GPT, Gemini, local)
- Fully offline after model download (~1.1GB one-time)
- No LLM cost per memory write
- 100% on-device — data never leaves your machine
- Profile isolation with `users --create` / `users --use`

### Limitations

- Requires agent cooperation — agent must call `save` + `kg-index` explicitly
- First-run latency (~5s for model warm-up)
- KG quality depends on agent extraction quality
- No automatic conversation compaction (agent manages what to save)
- Personal scale — not multi-tenant

---

## Feature Matrix

| Feature | Mem0 | Claude Code | OpenClaw | Kioku Lite |
|---|---|---|---|---|
| **Infrastructure** | Cloud-managed | Markdown files | SQLite per-agent | Single SQLite file |
| **BM25 keyword search** | ❌ | ❌ | ✅ (FTS5 on chunks) | ✅ (FTS5 on memories) |
| **Vector/semantic search** | ✅ (cloud) | ❌ | ✅ (per-chunk embeddings) | ✅ (FastEmbed ONNX, 1024-dim) |
| **Knowledge Graph** | ✅ (managed, Mem0g) | ❌ | ❌ | ✅ (open-schema, BFS traversal) |
| **Fused ranking (RRF)** | ✅ (reranker) | ❌ | ❌ | ✅ (BM25 + vector + KG) |
| **Entity recall** | ✅ | ❌ | ❌ | ✅ (`recall "entity"`) |
| **Connection queries** | ✅ (limited) | ❌ | ❌ | ✅ (`connect "A" "B"` → path) |
| **Entity listing** | ✅ | ❌ | ❌ | ✅ (`entities --limit N`) |
| **Timeline view** | ✅ (platform) | ❌ | ❌ | ✅ (`timeline`) |
| **LLM required** | ✅ (every write) | ❌ | ❌ | ❌ (agent-driven) |
| **Offline** | ❌ | ✅ | ❌ (needs gateway) | ✅ (after model download) |
| **Data on-device** | ❌ | ✅ | ✅ | ✅ |
| **User profile isolation** | ✅ (user/session/agent) | ❌ (per-project) | ✅ (per-agent) | ✅ (per-profile, `users` command) |
| **Auto memory** | ✅ (LLM extraction) | `MEMORY.md` (code insights) | ✅ (compaction) | ❌ (agent-explicit) |
| **Human-readable backup** | ❌ | ✅ (markdown files) | ❌ (SQLite only) | ✅ (markdown files) |
| **Git-trackable** | ❌ | ✅ | ❌ | ✅ |
| **Setup complexity** | API key + config | Zero | Gateway + openclaw.json | `pipx install` + `init` |
| **Target scale** | Enterprise / production | Project-scoped | Multi-agent system | Personal (1 user) |

---

## When to Use What

| Scenario | Best fit |
|---|---|
| Production app with many users | **Mem0** — managed infra, compliance, multi-tenant |
| Code assistant within a project | **Claude Code** (`CLAUDE.md`) — zero setup, project-scoped |
| Multi-agent chatbot system | **OpenClaw** — built-in agent isolation, conversation compaction |
| Personal long-term memory, offline | **Kioku Lite** — local-first, KG for causal queries, no LLM cost |
| Cross-domain entity tracking | **Kioku Lite** — graph connects entities across conversations |
| Air-gapped / private environment | **Kioku Lite** — 100% on-device, no data leaves machine |

### Complementary use

Kioku Lite is designed to **work alongside** the other tools, not replace them:

- **Claude Code + Kioku Lite:** Claude Code provides project context (`CLAUDE.md`), Kioku Lite provides personal memory and KG across all projects.
- **OpenClaw + Kioku Lite:** OpenClaw handles conversation management and agent routing, Kioku Lite adds structured long-term memory with entity tracking.
- **Mem0 + Kioku Lite:** Mem0 handles a production multi-user service, Kioku Lite handles the developer's own personal agent memory locally.

---

## Related

- [01-system.md](01-system.md) — Kioku Lite system architecture
- [04-kg-open-schema.md](04-kg-open-schema.md) — Open-schema entity and relationship types
