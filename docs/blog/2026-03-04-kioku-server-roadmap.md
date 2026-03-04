# Từ SQLite lên Cloud: Kiến trúc Kioku và lộ trình kioku-server

*Xuất bản: 2026-03-04 · v0.1.28*

Xin chào các bạn!

Vài ngày trước tôi đã chia sẻ [Kioku Lite](https://phuc-nt.github.io/kioku-lite-landing/) — bộ nhớ cá nhân cho AI Agent, chạy hoàn toàn local, không Docker, toàn bộ dữ liệu trong SQLite. Sau khi đăng, có hai câu hỏi xuất hiện nhiều nhất:

1. *"Graph search hoạt động chi tiết như thế nào?"*
2. *"Bản enterprise/cloud mà bạn đề cập sẽ trông như thế nào?"*

Bài viết này trả lời cả hai — cộng thêm so sánh chi tiết với MCP Memory Server chính thức của Anthropic, vì nhiều người đang dùng đó làm baseline để tham chiếu.

---

## Phần 1 — kioku-lite: Kiến trúc chi tiết

### Triết lý cốt lõi: SQLite là đủ (ở quy mô cá nhân)

Toàn bộ triết lý của kioku-lite là *"làm nhiều hơn với ít hơn"*. Thay vì chạy ChromaDB, FalkorDB, và Ollama server, mọi thứ đều nằm trong **một file `.db` duy nhất**:

```
~/.kioku-lite/users/<profile>/
├── data/kioku.db          ← SQLite: FTS5 + sqlite-vec + Knowledge Graph
└── memory/YYYY-MM/        ← Backup Markdown (đọc được, theo dõi được qua git)
    └── <content_hash>.md
```

Ba engine lưu trữ, một file:

| Engine | Extension SQLite | Mục đích |
|---|---|---|
| FTS5 | Built-in | Tìm kiếm từ khóa BM25 |
| sqlite-vec | Loadable extension | Vector ANN 1024 chiều |
| GraphStore | Bảng SQL thông thường | BFS traversal Entity-Relationship |

### Interface: CLI + SKILL.md

Lớp giao diện là **Typer CLI** (`kioku-lite`) cộng với file `SKILL.md` dạy bất kỳ agent nào cách sử dụng. Không cần SDK — nếu agent có thể chạy shell command, nó có thể dùng kioku-lite.

```
Agent (Claude Code / Cursor / Windsurf / OpenClaw)
    │
    ├─ kioku-lite save "..."            → lưu memory
    ├─ kioku-lite kg-index <hash>       → index entities vào KG
    ├─ kioku-lite search "..." --entities "A,B"
    ├─ kioku-lite recall "Entity"
    └─ kioku-lite connect "A" "B"
```

Thiết kế CLI-first này khiến kioku-lite **agnostic với mọi agent**: Claude, GPT, Gemini, model local — bất kỳ agent nào đọc được SKILL.md và gọi được shell command đều hoạt động.

### Tổng quan kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│                     INTERFACE LAYER                          │
│   cli.py (Typer) — 12 lệnh: save, search, kg-index,         │
│   recall, connect, entities, timeline, users, init, ...      │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│             KiokuLiteService  (service.py)                   │
│   save_memory() │ search() │ kg_index() │ recall()           │
└──────┬───────────────────┬─────────────────────┬─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
 MarkdownStore         Embedder              KiokuDB
 ~/memory/*.md        FastEmbed             (single .db)
 (backup con người)   ONNX local    ┌────────────────────────┐
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

### Write pipeline: save → kg-index

Mỗi memory tuân theo giao thức ghi hai bước — cả hai bước đều do agent gọi:

```
Bước 1: kioku-lite save "text" --mood MOOD --event-time YYYY-MM-DD
        │
        ├─ SHA256(text) → content_hash  (khóa dedup toàn cục)
        ├─ FastEmbed.embed("passage: " + text) → vector 1024 chiều
        ├─ MarkdownStore → ~/memory/YYYY-MM/<hash>.md
        ├─ SQLiteStore.upsert_memory() → FTS5 (index BM25)
        └─ SQLiteStore.upsert_vector() → sqlite-vec

Bước 2: kioku-lite kg-index <hash> --entities '[...]' --relationships '[...]'
        │
        ├─ Agent tự extract entities từ context (không gọi thêm LLM!)
        ├─ GraphStore.upsert_node() → kg_nodes (mention_count++)
        └─ GraphStore.upsert_edge() → kg_edges (với source_hash + event_time)
```

**Quyết định thiết kế quan trọng**: kioku-lite không bao giờ gọi LLM nội bộ. Agent đang gọi kioku-lite *chính là* LLM — nó extract entities trong bước reasoning của mình, rồi truyền vào `kg-index`. Không chi phí thêm. Không latency thêm. Không bị lock vào vendor.

### Search pipeline: tri-hybrid → RRF

```
kioku-lite search "query" --entities "Mẹ,Sato"
         │
         ▼
1. FastEmbed.embed("query: " + text) → vector 1024 chiều
         │
         ├─────────────────────────────────────┐
         ▼                   ▼                 ▼
  BM25 Search        Semantic Search     Graph Search
  (FTS5 MATCH)       (sqlite-vec ANN)    (BFS traversal)
  top-K theo BM25    top-K theo cosine   memories liên kết
  keyword hits       similarity          với entities
         │                   │                 │
         └─────────────────────────────────────┘
                             ▼
              Reciprocal Rank Fusion (RRF)
              hằng số k=60, fused scores
                             │
                             ▼
              Top-N kết quả đã dedup
              (key bởi content_hash)
```

Ba tín hiệu, kết hợp mà không cần train ranker:

| Tín hiệu | Bắt được gì |
|---|---|
| BM25 | Tên chính xác, ngày tháng, từ khóa (an toàn với tiếng Việt/đa ngôn ngữ) |
| Vector | Semantic similarity — "căng thẳng" khớp với "lo lắng" |
| Graph | Memories liên kết với entity — tất cả edges kết nối với "Mẹ" |

### Graph search: bài toán hub node (đã giải trong v0.1.27–0.1.28)

Trong personal KG, entity của chính người dùng (ví dụ "Phúc") xuất hiện trong gần như mọi memory. Với 30+ edges, traverse từ entity này trả về 90%+ tổng số memory — không có signal.

Chúng tôi đã giải quyết theo ba lớp:

**Task 1A — Loại self-entity (v0.1.27)**
```python
# Phát hiện hub: entity có mention_count cao nhất
self_entity = store.get_top_entity()  # → "Phúc" (33 lần đề cập)

# Nếu có seed khác, loại hub khỏi traversal
if self_entity and có_seed_khác:
    seeds = [e for e in seeds if e.name.lower() != self_entity.lower()]
```

**Task 1C — Adaptive hop limit (v0.1.27)**
```python
degree = store.get_degree(entity_name)
effective_hops = 1 if degree > 15 else max_hops  # hub → 1 hop, thường → 2
```

**Task 2E — Multi-entity intersection (v0.1.28)**
```
Khi 2+ seeds: trả về memories có thể đến được từ TẤT CẢ seeds (intersection)
Fallback sang union nếu intersection rỗng
```

Kết quả: tìm kiếm `--entities "Mẹ,Sato"` giờ trả về memories về Mẹ *và* Sato cùng nhau — không phải 92% tổng số memories.

---

## Phần 2 — kioku-server: Lộ trình

### Cùng core logic, khác infrastructure

kioku-lite đã chứng minh các thuật toán hoạt động. kioku-server lấy cùng core — tri-hybrid search, RRF fusion, agent-driven KG, open schema — và thay infrastructure để phục vụ enterprise:

```
kioku-lite                        kioku-server (kế hoạch)
─────────────────────────         ────────────────────────────────
Interface: CLI + SKILL.md    →    Interface: MCP Server
Embedding: FastEmbed ONNX    →    Embedding: Ollama / cloud API
Vector DB: sqlite-vec         →    Vector DB: ChromaDB (dedicated)
Graph DB:  Bảng SQLite        →    Graph DB:  FalkorDB (Cypher)
Scale:     1 user, local      →    Scale:     multi-tenant, cloud
```

Service layer (`KiokuService`) giữ nguyên. Thuật toán giữ nguyên. Chỉ I/O adapters thay đổi.

### Kiến trúc: kioku-server

```
┌───────────────────────────────────────────────────────────────┐
│                   MCP SERVER LAYER                            │
│   MCP tools: memory/save, memory/search, memory/kg-index,    │
│              memory/recall, memory/connect, memory/entities   │
└──────────────────────────┬────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              KiokuService  (core logic dùng chung)           │
│   save_memory() │ search() │ kg_index() │ recall()           │
└──────┬───────────────────┬─────────────────────┬─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
  PostgreSQL /         Embedder              Dedicated DBs
  Object Storage       Ollama / API  ┌──────────────────────────┐
  (lưu memory,         (hoặc local   │  ChromaDB                │
  export Markdown)     ONNX)         │  (vector store)          │
                                     │                          │
                                     │  FalkorDB                │
                                     │  (property graph,        │
                                     │   Cypher queries)        │
                                     └──────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Multi-Tenant Isolation                          │
│  API key → namespace → data isolation riêng mỗi tenant      │
│  (cùng pattern với multi-user profiles trong kioku-lite)     │
└──────────────────────────────────────────────────────────────┘
```

### Điểm khác biệt so với kioku-lite

| Khía cạnh | kioku-lite | kioku-server |
|---|---|---|
| **Interface** | CLI + SKILL.md | MCP Server (JSON-RPC) |
| **Embedding** | FastEmbed ONNX (local) | Ollama / cloud API (cấu hình được) |
| **Vector store** | sqlite-vec (in-process) | ChromaDB (dedicated container) |
| **Graph store** | SQLite tables + BFS | FalkorDB (property graph, Cypher) |
| **Scale** | 1 user, máy cá nhân | Multi-tenant, deploy lên cloud |
| **Auth** | Profile switching (`users --use`) | API keys per tenant |
| **Deployment** | `pipx install` | Docker Compose / Kubernetes |

### Điểm giữ nguyên

- **Core algorithms**: tri-hybrid search, RRF fusion, self-entity exclusion, adaptive hops, multi-entity intersection
- **Knowledge graph schema**: open-schema entity types, relationship types, evidence fields
- **Agent-driven KG**: không có LLM extraction nội bộ — agent vẫn tự làm
- **Content hash**: SHA256 dedup key liên kết memories qua tất cả storage layers
- **Multi-profile support**: cùng khái niệm isolation, thực hiện via API namespaces

### Tại sao MCP interface cho server?

Hệ sinh thái agent đang hội tụ về MCP (Model Context Protocol) như chuẩn tích hợp tool. Với CLI tool cá nhân, SKILL.md đơn giản hơn — không cần background process, chỉ cần shell command. Với enterprise server phục vụ nhiều agent và users, MCP là lựa chọn tự nhiên:

- Protocol discovery chuẩn
- Hoạt động với Claude Desktop, Cline, Cursor, và mọi MCP-compatible client
- Server xử lý auth, rate limiting, tenant isolation
- Agent không cần cài gì — chỉ cần trỏ vào endpoint của server

---

## Phần 3 — So sánh với MCP Memory Server của Anthropic

Anthropic cung cấp [MCP Memory Server chính thức](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) như reference implementation trong kho MCP servers. Vì cả kioku-server và MCP Memory Server đều cung cấp memory qua MCP tools, việc so sánh trực tiếp rất hữu ích.

### MCP Memory Server là gì?

MCP Memory Server là một **TypeScript reference implementation** cung cấp cho agent một knowledge graph đơn giản lưu trong file JSONL flat file. Nó expose 6 MCP tools:

- `create_entities` — thêm entity nodes
- `create_relations` — thêm typed relations giữa entities
- `add_observations` — gắn facts vào entities
- `delete_entities` / `delete_relations` / `delete_observations`
- `search_nodes` — tìm entities theo tên (string match)
- `read_graph` — trả về toàn bộ graph

Storage là một file `.jsonl` với mỗi dòng là JSON object đại diện entity hoặc relation. Mỗi lần `search_nodes` lọc list đó theo string match.

### Tương phản kiến trúc

```
MCP Memory Server                    kioku-server (kế hoạch)
─────────────────────────            ──────────────────────────────
Storage: JSONL flat file             Storage: ChromaDB + FalkorDB
Search:  String match only           Search:  Tri-hybrid (BM25 + vector + KG)
Embedding: Không có                  Embedding: Ollama / cloud API
Graph:   Flat entity list            Graph:   Property graph (Cypher)
Scale:   Single user, local file     Scale:   Multi-tenant, cloud
Language: TypeScript                 Language: Python
Interface: 6 MCP tools               Interface: MCP tools (cùng protocol)
```

### So sánh tính năng

| Tính năng | MCP Memory Server | kioku-lite | kioku-server (kế hoạch) |
|---|---|---|---|
| **Storage** | JSONL flat file | SQLite file duy nhất | ChromaDB + FalkorDB + PostgreSQL |
| **BM25 keyword search** | ❌ | ✅ (SQLite FTS5) | ✅ |
| **Semantic / vector search** | ❌ | ✅ (FastEmbed ONNX) | ✅ (cloud-scale) |
| **Knowledge Graph traversal** | ❌ (flat list, không BFS) | ✅ (BFS, adaptive hops) | ✅ (FalkorDB Cypher) |
| **Fused ranking (RRF)** | ❌ | ✅ | ✅ |
| **Entity recall** | Partial (lọc list) | ✅ `recall "entity"` | ✅ |
| **Causal chains / paths** | ❌ | ✅ `connect "A" "B"` | ✅ |
| **Timeline / temporal queries** | ❌ | ✅ `--from --to` | ✅ |
| **Multi-entity intersection** | ❌ | ✅ (v0.1.28) | ✅ |
| **Hub node exclusion** | ❌ | ✅ (v0.1.27) | ✅ |
| **Multi-tenant** | ❌ | ❌ (profile-based) | ✅ |
| **Đa ngôn ngữ** | ❌ | ✅ (100+ ngôn ngữ) | ✅ |
| **Offline** | ✅ | ✅ | Cấu hình được |
| **Backup đọc được** | ❌ | ✅ Markdown | ✅ Markdown export |
| **Production-ready** | ❌ (reference impl) | Quy mô cá nhân | Có |
| **Ngôn ngữ** | TypeScript | Python | Python |

### Triết lý: reference vs production

MCP Memory Server **cố tình đơn giản**. Đây là reference implementation cho developer hiểu cách xây memory tools với MCP — điểm khởi đầu, không phải điểm kết thúc. Anthropic cung cấp nó như template để fork và điều chỉnh.

kioku-lite và kioku-server là công cụ production-grade xây cho agent thực tế làm việc thực tế:

> **MCP Memory Server**: "Đây là cách memory tools có thể hoạt động. Hãy mở rộng cái này."
>
> **kioku-lite**: "Memory lưu trong SQLite với semantic search thực, graph traversal, và temporal queries. Dùng được ngay, quy mô cá nhân."
>
> **kioku-server**: "Cùng thuật toán, infrastructure enterprise. Team memory, multi-tenant cloud."

### Khác biệt thực tế: chất lượng tìm kiếm

Khoảng cách rõ ràng nhất là chất lượng search. Với 50 memories về cuộc sống hàng ngày:

| Query | MCP Memory Server | kioku-lite |
|---|---|---|
| "căng thẳng về dự án" | Trả về entities tên "căng thẳng" hoặc "dự án" | Trả về memories tương tự ngữ nghĩa (vector) + memories liên kết qua entity (KG) |
| Memories về Mẹ | Tìm entity node "Mẹ" | BFS qua tất cả edges từ node Mẹ, kết hợp với semantic matches |
| "điều gì gây ra lo âu tháng trước" | Không có temporal filter, không có causal traversal | `--from 2026-02-01 --to 2026-02-28` + KG paths `TRIGGERED_BY` |
| Memories kết nối Mẹ và Sato | Không có graph traversal | `connect "Mẹ" "Sato"` trả về relationship path |

---

## Tổng kết

```
kioku-lite (hiện tại)  kioku-server (kế hoạch)   MCP Memory Server
────────────────────   ──────────────────────     ─────────────────
Quy mô cá nhân        Enterprise / Cloud          Reference impl
CLI interface          MCP interface               MCP interface
SQLite-everything      Independent DBs             JSONL flat file
Tri-hybrid search      Tri-hybrid + cloud DBs      String match only
Agent-driven KG        Agent-driven KG             Agent-driven KG
0 Docker               Docker Compose / K8s        0 infrastructure
v0.1.28 · sẵn dùng    Đang phát triển             Sẵn (TypeScript)
```

**Dùng kioku-lite nếu:** Bạn muốn long-term memory cá nhân cho coding/journaling agent, ngay bây giờ, không cần infra, dùng được offline.

**Dùng kioku-server nếu:** Bạn đang xây hệ thống multi-agent hoặc enterprise deployment với nhiều user dùng chung memory backend. (Chưa có — đang phát triển.)

**Dùng MCP Memory Server nếu:** Bạn muốn điểm khởi đầu đơn giản để hiểu cách MCP memory tools hoạt động, hoặc muốn xây custom memory layer của riêng mình.

---

- GitHub: [github.com/phuc-nt/kioku-agent-kit-lite](https://github.com/phuc-nt/kioku-agent-kit-lite)
- Homepage: [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)
- Changelog: [CHANGELOG.md](https://github.com/phuc-nt/kioku-agent-kit-lite/blob/main/CHANGELOG.md)

Cảm ơn đã đọc! Nếu bài viết này giúp bạn hiểu rõ hơn về kiến trúc, một ⭐ trên GitHub là động lực rất lớn.
