# Từ CLI tới Server: Kiến trúc Kioku và lộ trình kioku-server

*Xuất bản: 2026-03-04 · v0.1.28*

Xin chào các bạn!

Bài viết này trả lời hai câu hỏi hay gặp sau [bài giới thiệu kioku-lite](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro-vn): kiến trúc hoạt động như thế nào trong thực tế, và dự án đang hướng đến đâu với kioku-server. Cộng thêm so sánh với MCP Memory Server chính thức của Anthropic.

---

## Phần 1 — kioku-lite tóm tắt

kioku-lite lưu trữ mọi thứ trong **một file SQLite duy nhất** — không Docker, không server ngoài. Giao diện là **CLI + SKILL.md**: bất kỳ agent nào chạy được shell command đều đọc được skill file và có memory ngay lập tức.

Cốt lõi là **tri-hybrid search** kết hợp ba tín hiệu qua RRF (Reciprocal Rank Fusion):

| Tín hiệu | Công nghệ | Tìm được gì |
|---|---|---|
| BM25 | SQLite FTS5 | Từ khóa chính xác, tên, ngày |
| Vector | sqlite-vec + FastEmbed ONNX | Memories tương tự ngữ nghĩa |
| Knowledge Graph | SQLite BFS | Memories liên kết entity, chuỗi nhân quả |

Ghi dữ liệu theo giao thức hai bước do agent tự gọi: `save` (text → SHA256 hash + embedding + FTS5) rồi `kg-index` (agent extract entities → GraphStore). **Không có LLM nội bộ** — agent đang gọi chính là LLM.

Cải tiến graph search v0.1.27–0.1.28: loại self-entity khỏi BFS seeds (hub node), adaptive hop limit (degree > 15 → 1 hop), và multi-entity intersection (chỉ trả về memories có thể đến từ *tất cả* seed entities).

*→ Chi tiết đầy đủ: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) · [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) · [Search Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture)*

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
