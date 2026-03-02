# Memory Comparison — Kioku Lite vs Claude Code vs OpenClaw

---

## Summary

Three different approaches to agent memory, each with a different design philosophy:

| System | Memory Model | Persistence | Search | Knowledge Graph |
|---|---|---|---|---|
| **Claude Code** | Flat markdown files | Session-scoped + `CLAUDE.md` / `MEMORY.md` | None (context window only) | ❌ |
| **OpenClaw** | SQLite chunks + embeddings | Per-agent SQLite database | Semantic (embedding-based) | ❌ |
| **Kioku Lite** | SQLite + Markdown + KG | Per-profile isolated stores | Tri-hybrid (BM25 + vector + KG) | ✅ Agent-driven |

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

### Strengths

- Three search signals fused → higher recall than any single method
- Knowledge graph enables `recall "Alice"`, `connect "Alice" "Project X"`, `entities`
- Agent-driven extraction works with any LLM (Claude, GPT, Gemini, local)
- Fully offline after model download (~1.1GB one-time)
- Profile isolation with `users --create` / `users --use`

### Limitations

- Requires agent cooperation — agent must call `save` + `kg-index` explicitly
- First-run latency (~5s for model warm-up)
- KG quality depends on agent extraction quality
- No automatic conversation compaction (agent manages what to save)

---

## Feature Matrix

| Feature | Claude Code | OpenClaw | Kioku Lite |
|---|---|---|---|
| **BM25 keyword search** | ❌ | ✅ (FTS5 on chunks) | ✅ (FTS5 on memories) |
| **Vector/semantic search** | ❌ | ✅ (per-chunk embeddings) | ✅ (FastEmbed ONNX, 1024-dim) |
| **Knowledge Graph** | ❌ | ❌ | ✅ (open-schema, BFS traversal) |
| **Entity recall** | ❌ | ❌ | ✅ (`recall "entity"`) |
| **Connection queries** | ❌ | ❌ | ✅ (`connect "A" "B"` → path) |
| **Entity listing** | ❌ | ❌ | ✅ (`entities --limit N`) |
| **Timeline view** | ❌ | ❌ | ✅ (`timeline`) |
| **User profile isolation** | ❌ (per-project) | ✅ (per-agent) | ✅ (per-profile, `users` command) |
| **Auto memory** | `MEMORY.md` (code insights) | ✅ (compaction) | ❌ (agent-explicit) |
| **Human-readable backup** | ✅ (markdown files) | ❌ (SQLite only) | ✅ (markdown files) |
| **Git-trackable** | ✅ | ❌ | ✅ |
| **Offline** | ✅ | ❌ (needs gateway) | ✅ (after model download) |
| **Setup complexity** | Zero | Gateway + openclaw.json | `pipx install` + `init` |

---

## When to Use What

| Scenario | Best fit |
|---|---|
| Code assistant within a project | Claude Code (`CLAUDE.md`) — zero setup, project-scoped |
| Multi-agent chatbot system | OpenClaw — built-in agent isolation, conversation compaction |
| Personal long-term memory with recall | **Kioku Lite** — KG enables "who/what/when" queries across months of data |
| Cross-domain entity tracking | **Kioku Lite** — graph connects entities across conversations |

### Complementary use

Kioku Lite is designed to **work alongside** both Claude Code and OpenClaw, not replace them:

- **Claude Code + Kioku Lite:** Claude Code provides project context (`CLAUDE.md`), Kioku Lite provides personal memory and KG across all projects.
- **OpenClaw + Kioku Lite:** OpenClaw handles conversation management and agent routing, Kioku Lite adds structured long-term memory with entity tracking.

---

## Related

- [01-system.md](01-system.md) — Kioku Lite system architecture
- [04-kg-open-schema.md](04-kg-open-schema.md) — Open-schema entity and relationship types
