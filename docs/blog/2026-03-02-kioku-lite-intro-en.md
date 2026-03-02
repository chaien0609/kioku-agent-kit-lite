# Kioku: Why I built a Knowledge Graph memory engine for my AI agents

Hey builders and open-source community!

Today I want to share a side-project I've been building to solve a very personal pain point that I believe many of you also face: **How do you give AI a real "long-term memory" that understands emotions and causal relationships?**

That's why **Kioku** was born. It's an ultra-lightweight Personal Memory Engine, runs entirely local, designed specifically for AI Agents.

![kioku-lite homepage](img/image.png)
*Homepage: [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)*

## The origin: A journal-writer's frustration

I'm someone who journals daily. I like to self-reflect and look back at past events. In the age of AI, I've tried many tools and chatbots for this, but the results were always disappointing.

The core problem: **No tool truly solves the challenge of storing, analyzing emotions, and understanding causal relationships between actions.**

Popular agents today (even the big names) have "long-term memory" features, but they essentially just store flat text or vectors stuffed into a context window. When you ask *"Why was I stressed about project X last month?"*, the system gets confused because it can't connect event A (argument with boss) leading to emotion B (stress) and decision C (switching projects). It lacks **connection**.

## The solution: An open memory engine for any agent

As a daily user of AI tools, especially coding agents (Claude Code, Windsurf, Cursor), I realized: Instead of building a new bot from scratch, why not create an independent *memory organ* that plugs into our favorite agents?

The goal was to make it **compatible with as many agents as possible**. That's why for the lite version (kioku-lite), I chose an architecture based on **CLI** and **SKILLS files** (specifically the `AGENTS.md` & `SKILL.md` format popular among CLI agents today). With just a few commands, any agent can learn to read/write memories.

## Architecture overview: Write, search, and comparison

Kioku Lite uses a **Tri-hybrid** search mechanism running 100% on SQLite:
1. **BM25 (FTS5):** Exact keyword search.
2. **Vector (sqlite-vec + FastEmbed ONNX):** Semantic search (runs local, no API needed).
3. **Knowledge Graph (GraphStore):** Entity graph with causal relationships.

Here's the system overview:

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

The protocol has 2 main phases, orchestrated by the agent:

### 1. Write phase
When a new event occurs: The agent saves text (`save`) then autonomously extracts entities/relationships and indexes them into the Graph (`kg-index`). Everything runs locally, no hidden LLM calls.

### 2. Search phase
When context is needed: The agent calls `search`. Results go through 3 separate pipelines and are fused via RRF (Reciprocal Rank Fusion):

```
┌──────────────────────────────────────────────────────────────┐
│                  kioku-lite search "query"                   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│           1. Embed Query (FastEmbed 1024-dim ONNX)           │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 2. Tri-hybrid Search Engines                 │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │   BM25 Search  │  │ Semantic Search│  │  Graph Search  │  │
│  │ (SQLite FTS5)  │  │  (sqlite-vec)  │  │  (SQLite BFS)  │  │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  │
└──────────┼───────────────────┼───────────────────┼───────────┘
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│    3. Reciprocal Rank Fusion (RRF) & Deduplication           │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Final Merged Results                      │
└──────────────────────────────────────────────────────────────┘
```

### Memory model comparison

How does Kioku Lite compare to familiar systems?

| System | Memory Model | Persistence | Search | Knowledge Graph |
|---|---|---|---|---|
| **Claude Code** | Flat markdown files | Session-scoped + `CLAUDE.md` / `MEMORY.md` | None (context window only) | No |
| **OpenClaw** | SQLite chunks + embeddings | Per-agent SQLite database | Semantic (embedding-based) | No |
| **Kioku Lite** | SQLite + Markdown + KG | Per-profile isolated stores | Tri-hybrid (BM25 + vector + KG) | Yes (Agent-driven) |

*(Deep dive: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) | [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) | [Search Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture) | [Memory Comparison](https://phuc-nt.github.io/kioku-lite-landing/blog.html#memory-comparison))*

## Knowledge Graph (KG): The key to flexibility

Another strength of Kioku Lite is the **Open Schema** for its Knowledge Graph. Entity types (`entity_type`) and relationship types (`rel_type`) are flexible strings, not locked into fixed enums.

Kioku-lite ships with **2 built-in personas**:
- **Companion**: Agent extracts `EMOTION`, `LIFE_EVENT` nodes linked by `TRIGGERED_BY`. Ideal for journaling and emotion tracking.
- **Mentor**: Agent extracts `DECISION`, `LESSON` nodes linked by `LED_TO`. Ideal for self-reflection and learning from experience.

You can also ask your agent to configure entirely new personas for any domain you need, such as HR management, product management, or any other field where you want your agent to remember things in a specific way.

*(Schema details: [KG Open Schema](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kg-open-schema))*

## Setup in one copy-paste

Two setup guides are ready for the 2 agent types I use daily:

1. **[General Agent Setup (Claude Code, Cursor, Windsurf)](https://phuc-nt.github.io/kioku-lite-landing/agent-setup.html)**
2. **[OpenClaw Agent Setup](https://phuc-nt.github.io/kioku-lite-landing/openclaw-setup.html)**

Just copy the relevant guide and paste it to your agent. It will auto-run setup, configure identity, and connect to the memory engine on your machine.

Full details at [Kioku Lite Homepage](https://phuc-nt.github.io/kioku-lite-landing/).

## Kioku Lite vs Kioku Full

**kioku-lite** ships first, targeting Personal Users. Setup is fast via `pipx`, no Docker, no API keys, no external databases like ChromaDB/FalkorDB. Runs silently in the background on your personal machine.

Meanwhile, **kioku-full** with dedicated graph and vector databases, multi-tenant Enterprise support, is still under active development.

## Closing

If you're a builder, an open-source enthusiast, and especially if you're still looking for a "long-term memory" solution that helps AI understand emotions and causality like a real companion, give **Kioku Lite** a try.

- Homepage: **[phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)**
- GitHub: **[github.com/phuc-nt/kioku-agent-kit-lite](https://github.com/phuc-nt/kioku-agent-kit-lite)**

Your feedback and support at this stage means the world. Try it out, share it with anyone who needs it, or simply drop a Star on the repo!

Thanks for reading! Happy coding and looking forward to your feedback!
