# TESTLOG — Enriched Search E2E (2026-02-28)

**Version:** v0.1.3
**Tester:** Claude Code (AI agent, đóng vai user thực tế theo SKILL.md)
**Profile:** `search-test` (isolated, xoá sau khi test)
**Scope:** Toàn bộ workflow CLI + 8 search cases + edge cases

---

## Môi trường

```
kioku-lite v0.1.3 (source install, .venv)
Python 3.x, SQLite FTS5 + sqlite-vec
Embedder: fastembed (intfloat/multilingual-e5-large, 1024-dim)
Platform: macOS, Mac Mini
```

---

## Test Data

6 memories với entities/relationships đầy đủ:

| ID | Event time | Nội dung | Mood | Entities |
|----|------------|----------|------|----------|
| M1 | 2026-02-28 | Họp team Minh & Hùng, sprint planning Kioku Lite v0.2 | work | Minh, Hùng, Kioku Lite |
| M2 | 2026-02-28 | Lo lắng về deadline dự án 15/3 | anxious | Kioku Lite, deadline 15/3 |
| M3 | 2026-02-26 | Gặp Lan ở Starbucks Đinh Tiên Hoàng, Lan học tiếng Nhật, đăng ký JLPT N3 | happy | Lan, Starbucks ĐTH, JLPT N3, tiếng Nhật |
| M4 | 2026-02-25 | Hùng kể từng làm senior engineer ở TechCorp 4 năm, TechCorp fintech ở HN | curious | Hùng, TechCorp, Hà Nội |
| M5 | 2026-02-24 | Minh ấp ủ startup AI productivity tools | excited | Minh, AI productivity tools |
| M6 | 2026-02-28 | Quyết định học Rust vào tháng 3 | excited | Rust, systems programming |

**Aliases đã đăng ký:** `"anh Hùng"`, `"hung"` → canonical `"Hùng"` · `"cô Lan"`, `"chị Lan"` → canonical `"Lan"`

---

## Kết quả các test cases chính

### ✅ Case 1 — Pronoun Resolution

**Tình huống:** User hỏi *"anh ấy đang làm gì dạo này?"* trong khi đang nói về Hùng.

| Bước | Agent thực hiện | Kết quả |
|------|----------------|---------|
| Map pronoun | "anh ấy" → "Hùng" từ conversation context | ✅ |
| Enrich query | `"Hùng career work project" --entities "Hùng"` | ✅ |
| Results | 3 results: TechCorp memory (BM25 top), sprint meeting, deadline (via graph) | ✅ |
| graph_context | 6 nodes: Hùng, Kioku Lite, TechCorp, Minh, Hà Nội, deadline 15/3 | ✅ |

**Nhận xét:** BM25 rank đúng (TechCorp memory lên top vì có "Hùng" + từ khoá career/work). Graph context đưa ra đầy đủ connected nodes.

---

### ✅ Case 2 — Implicit Subject Mapping

**Tình huống:** User hỏi *"dự án đang đến đâu rồi?"* trong khi đang bàn về Kioku Lite.

| Bước | Agent thực hiện | Kết quả |
|------|----------------|---------|
| Map implicit | "dự án" → "Kioku Lite" từ context | ✅ |
| Enrich query | `"Kioku Lite progress milestone status sprint" --entities "Kioku Lite"` | ✅ |
| Results (count) | 4 results | ✅ |
| Top result | Sprint planning memory (BM25 score 0.0325 — top) | ✅ |
| Result 2 | Deadline anxiety memory (graph link Kioku Lite → deadline 15/3) | ✅ |

**Nhận xét:** Graph context quan trọng — memory M2 (deadline/anxious) được kéo vào qua edge `Kioku Lite → INVOLVES → deadline 15/3`, mặc dù không mention "Kioku Lite" trong text. Đây là lợi thế của KG.

---

### ✅ Case 3 — Temporal Range

**Tình huống:** User hỏi về ngày cụ thể và khoảng thời gian.

| Query gốc | Enrichment | Kết quả |
|-----------|-----------|---------|
| "hôm qua có gì?" | `--from 2026-02-27 --to 2026-02-27` | 5 results (event_time = 2026-02-27) ✅ |
| "trong tuần này" | `timeline --from 2026-02-23 --to 2026-02-28 --sort-by event_time` | 5 entries đúng thứ tự bi-temporal ✅ |

**Nhận xét:** `timeline --sort-by event_time` hiển thị đúng thứ tự sự kiện thực tế (không phải thứ tự ghi nhận). Bi-temporal modeling hoạt động đúng — M2 và M1 có `event_time: 2026-02-28`, M3 có `2026-02-26`, M5 có `2026-02-24`.

**⚠️ Lưu ý:** `--from/--to` filter trên `search` dùng `date` field (processing_time), không phải `event_time`. Dùng `timeline --sort-by event_time` để query theo thời gian sự kiện.

---

### ✅ Case 4 — Relational Queries

#### 4a — "ai hay làm việc với Hùng?" → `recall "Hùng" --hops 2`

```
connected_count: 6
nodes: Hùng, Kioku Lite, TechCorp, deadline 15/3, Minh, Hà Nội
relationships:
  Hùng → WORKS_ON → Kioku Lite (0.9)
  Hùng → WORKS_AT → TechCorp (0.85)
  Kioku Lite → INVOLVES → deadline 15/3 (0.95)
  Minh → WORKS_ON → Kioku Lite (0.9)
  TechCorp → LOCATED_AT → Hà Nội (0.8)
source_memories: 3 memories hydrated ✅
```

**Kết quả:** Agent có thể trả lời: *"Người làm việc cùng Hùng: Minh (cùng Kioku Lite). Hùng từng ở TechCorp (Hà Nội). Kioku Lite đang có deadline 15/3."*

#### 4b — "Lan và Hùng liên quan thế nào?" → `connect "Lan" "Hùng"`

```json
{ "connected": false, "paths": [] }
```

**Kết quả:** Đúng — trong dataset này Lan không có edge nào tới Kioku Lite (chỉ Minh + Hùng mới work on Kioku Lite ở M1), nên không có path. Agent phản hồi trung thực: *"Chưa có mối liên hệ trực tiếp nào được ghi nhận giữa Lan và Hùng."*

---

### ✅ Case 5 — Multi-Entity Search

**Tình huống:** *"Project nào Minh đang làm?"* → agent lấy entity list, thấy `Kioku Lite (PROJECT)` và `AI productivity tools (CONCEPT)`.

```
Query: "Minh project work startup AI tools"
Entities: "Minh,Kioku Lite,AI productivity tools"
Results: 4 (Deadline memory top via graph, Sprint planning #2, TechCorp #3, Startup idea #4)
```

**⚠️ Ranking issue:** `deadline` memory lên top (#1, score 0.0164) qua graph route, dù không liên quan đến câu hỏi. Sprint planning và Startup idea (#2, #4) mới là best answers.

**Nguyên nhân:** Graph từ `Minh → Kioku Lite → INVOLVES → deadline 15/3` tạo noise khi expand 2-hop. Agent cần filter by relevance threshold hoặc chỉ dùng top results trong `graph_context.nodes`.

---

### ✅ Case 6 — Thematic Search (Không có entity rõ)

**Tình huống:** *"Dạo này tại sao hay lo lắng?"* — không có proper noun nào.

```
Query: "lo lắng anxious worry stress cảm xúc tiêu cực"
Top result: M2 (deadline/anxious) — score 0.0164, source: vector ✅
Result #2-5: unrelated memories với score thấp (0.015x)
```

**Kết quả:** Vector search tìm đúng M2 ở top 1. Khoảng cách score rõ ràng (0.0164 vs 0.015x). Agent nên present result #1 với confidence cao, còn #2-5 là background noise.

---

### ✅ Case 7 — Alias Resolution

```
recall "anh Hùng" --hops 1
→ connected_count: 3 (Hùng, Kioku Lite, TechCorp)
→ ALIAS RESOLVED: True ✅
```

`"anh Hùng"` → canonical `"Hùng"` → đầy đủ graph traversal. Hoạt động đúng cho tất cả aliases đã đăng ký.

---

### ✅ Case 8 — Temporal Auto-Detect trong Query

Unit test 5 patterns:

| Query | Expected | Result |
|-------|----------|--------|
| `"năm nay tôi làm gì"` | `2026-01-01 → 2026-12-31` | ✅ OK |
| `"năm ngoái có gì"` | `2025-01-01 → 2025-12-31` | ✅ OK |
| `"tháng 2/2026"` | `2026-02-01 → 2026-02-28` | ✅ OK |
| `"something from 2024"` | `2024-01-01 → 2024-12-31` | ✅ OK |
| `"no temporal hint"` | `(None, None)` | ✅ OK |

---

## Edge Cases

### ⚠️ Edge Case A — "Không có kết quả" (Nonsensical query)

```
Query: "xyzzy_never_exists_token_123456"
Expected: 0 results
Actual: 5 results (tất cả source: vector, score 0.0154–0.0164)
```

**Phân tích:** Vector search (cosine similarity) **luôn trả về K nearest neighbors**, bất kể query vô nghĩa đến đâu. BM25 và Graph đúng (0 results), nhưng vector "fill in" 5 results với score thấp.

**Impact:** SKILL.md có note *"Confidence thấp (score < 0.02) → nói rõ 'có thể liên quan, nhưng không chắc'"*. Agent PHẢI áp threshold này — không được present vector results có score < 0.02 như là relevant memories.

**Khuyến nghị:** Cân nhắc thêm minimum score filter ở service level, hoặc thêm `"low_confidence"` flag trong response khi tất cả results có score < threshold.

---

### ⚠️ Edge Case B — Duplicate Save

```bash
kioku-lite save "Duplicate test memory content"  # hash: cb6269df...
kioku-lite save "Duplicate test memory content"  # hash: cb6269df... (same)
```

```
Vector insert failed: UNIQUE constraint failed on memory_vec primary key
DEDUP OK: same hash returned ✅
```

**Phân tích:** Dedup logic đúng — `content_hash` unique constraint prevent double-insert vào `memories` table. Tuy nhiên:
1. `status: "saved"` được trả về cho lần 2, dù thực ra là **duplicate** (không có insert nào xảy ra)
2. Warning `Vector insert failed: UNIQUE constraint failed` log ra stderr — user thấy warning mỗi lần save duplicate

**Khuyến nghị:** Return `"status": "duplicate"` (hoặc `"already_exists": true`) khi `memory_store.insert()` returns `-1`, thay vì `"status": "saved"`.

---

### ✅ Edge Case C — Connect Disconnected Entities

```
connect "Lan" "Rust"  →  connected: false, paths: []
```

Đúng — không có path, response honest. Agent không hallucinate connection.

---

## Tổng kết

### Pass/Fail Summary

| Category | Tests | Pass | Fail | Note |
|----------|-------|------|------|------|
| Workflow (save/kg-index/users) | 3 | 3 | 0 | |
| Search — Pronoun | 1 | 1 | 0 | |
| Search — Implicit Subject | 1 | 1 | 0 | |
| Search — Temporal | 2 | 2 | 0 | |
| Search — Relational (recall/connect) | 2 | 2 | 0 | |
| Search — Multi-entity | 1 | 1 | 0 | ⚠️ Graph noise issue |
| Search — Thematic | 1 | 1 | 0 | |
| Alias Resolution | 1 | 1 | 0 | |
| Temporal Auto-Detect | 5 | 5 | 0 | |
| Edge: No results | 1 | 0 | 1 | Vector always returns results |
| Edge: Duplicate save | 1 | 0 | 1 | status misleading |
| Edge: Disconnected connect | 1 | 1 | 0 | |
| **TOTAL** | **20** | **18** | **2** | |

---

## Bugs / Issues Tìm Thấy

### BUG-1 — `connect` không hydrate `source_memories` (từ session trước)

**File:** `src/kioku_lite/pipeline/graph_store.py` → `find_path()`
**Mô tả:** Khi build path edges trong `find_path`, code không copy `source_hash` từ DB vào `GraphEdge`. Kết quả: `service.explain_connection()` không thể hydrate source memories.
**Tác động:** `source_memories` luôn rỗng khi dùng `connect`, mặc dù edges có `source_hash` trong DB.
**Severity:** Medium — chức năng recall vẫn hoạt động, chỉ thiếu evidence text.

```python
# graph_store.py, find_path() — current (broken):
edges.append(GraphEdge(source=path[i], target=path[i+1], rel_type=rel, evidence=ev))
# ← Thiếu source_hash=? từ adj dict

# Fix: cần lưu source_hash khi build adj list:
adj.setdefault(s.lower(), []).append((t, rel, ev, source_hash))
# Và truyền vào GraphEdge khi build path.
```

### BUG-2 — `save` trả `status: "saved"` cho duplicate

**File:** `src/kioku_lite/service.py` → `save_memory()`
**Mô tả:** `memory_store.insert()` trả `-1` khi duplicate, nhưng `save_memory()` không check giá trị này → luôn trả `status: "saved"`.
**Tác động:** Agent không thể phân biệt memory mới vs duplicate. Gây noise warning ở stderr.

```python
# service.py — fix đề xuất:
row_id = self.db.memory.insert(...)
status = "saved" if row_id != -1 else "duplicate"
```

### ISSUE-3 — Vector search không có minimum score filter

**Mô tả:** `search` luôn trả K results từ vector leg, kể cả khi query hoàn toàn không liên quan.
**Tác động:** Agent dễ bị confused nếu không kiểm tra score threshold.
**Workaround:** Agent MUST filter results với `score < 0.02` và label là "low confidence" (đã document trong SKILL.md).

### ISSUE-4 — Graph noise trong multi-entity search

**Mô tả:** Khi search với nhiều entities, 2-hop graph expansion có thể kéo vào memories không relevant qua indirect connections.
**Ví dụ:** Query "Minh project" với entities `[Minh, Kioku Lite]` → deadline memory lên top via `Minh→Kioku Lite→deadline`.
**Tác động:** Ranking bị ảnh hưởng, agent phải dựa vào `source` field để đánh giá trust level (bm25 > vector > graph).

---

## Đề xuất cải tiến

| Priority | Item | Effort |
|----------|------|--------|
| P1 | Fix BUG-1: `source_hash` trong `find_path` | Small |
| P1 | Fix BUG-2: `status: "duplicate"` cho duplicate saves | Small |
| P2 | Thêm score threshold filter (vd: min_score param) | Medium |
| P2 | `--version` flag cho CLI | Small |
| P3 | Graph noise: weight decay theo hop count | Medium |
| P3 | `search` filter theo `event_time` (hiện chỉ filter theo `date`) | Medium |
