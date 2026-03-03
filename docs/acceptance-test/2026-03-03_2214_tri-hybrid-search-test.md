# Acceptance Test: Tri-Hybrid Search & Agent Integration

**Date:** 2026-03-03 22:14  
**Version:** kioku-lite 0.1.25  
**Agent model:** claude-sonnet-4-5 (OpenClaw)  
**Profile:** companion (Emotional Companion)  
**DB state:** 36 memories, 79 nodes, 87 edges  

---

## 1. Test Scenario

Agent session đã bị clear (không có chat history). DB giữ nguyên.  
Mục tiêu: kiểm tra agent có thể hiểu user hoàn toàn từ kioku-lite DB, và tri-hybrid search có hoạt động đúng thiết kế không.

---

## 2. Agent Commands Used (this session)

| Command | Count | Purpose |
|---|---|---|
| `search` | 6x | Tìm context cho câu hỏi |
| `users` | 1x | Session start — verify profile |
| `recall` | 1x | Entity traversal (Phong) |
| `save` | 3x | Lưu thông tin mới (tự động, không thông báo user) |
| `kg-index` | 3x | Index entities sau mỗi save |

---

## 3. Search Query Analysis

### Query 1: Session Start
```
kioku-lite search "Phúc profile background goals recent" --limit 10
```

| Metric | Value |
|---|---|
| Total results | 10 |
| Sources | **vector: 10** |
| Hydrated (original text) | ✅ 10/10 |
| Has event_time | 9/10 |

**Nhận xét:** Chỉ có vector search trả kết quả. BM25 không match vì query tiếng Anh ("profile background goals") không khớp keyword tiếng Việt trong FTS. Graph không trigger vì không có `--entities`.

---

### Query 2: "tôi có ghét mẹ không?"
```
kioku-lite search "mẹ cảm xúc giận relationship mother feelings" --limit 15
```

| Metric | Value |
|---|---|
| Total results | 15 |
| Sources | **vector: 15** |
| Hydrated | ✅ 15/15 |
| Has event_time | 14/15 |
| Top result | "Ký ức mẹ đánh roi (thời nhỏ)" — score 0.0328 |

**Nhận xét:** Vector search dominant. Query enrichment tốt (bilingual: "mẹ cảm xúc giận" + "mother feelings"). Kết quả rất relevan — toàn memories liên quan đến mẹ. Agent trả lời phân tích cảm xúc sâu sắc.

---

### Query 3: "tôi và Phong quan hệ thế nào?"
```
kioku-lite search "Phong relationship memories kỉ niệm" --limit 15
```

| Metric | Value |
|---|---|
| Total results | 15 |
| Sources | **vector: 15** |
| Hydrated | ✅ 15/15 |
| Has event_time | 14/15 |

**Nhận xét:** "Phong" không nằm trong KG nodes (agent index là "Con trai" thay vì "Phong"). Vector search vẫn tìm được, nhưng kết quả chưa chính xác lắm (top-1 là "quan hệ cha-con" chung chung, không phải về Phong cụ thể).

---

### Query 4: Follow-up Phong
```
kioku-lite search "Phong con trai anh em" --limit 20
```

| Metric | Value |
|---|---|
| Total results | 20 |
| Sources | **bm25: 1, vector: 19** |
| Hydrated | ✅ 20/20 |
| Has event_time | 19/20 |
| Top result (BM25) | "Phong Vy 3 tuổi - Dạy con về anh em" — score 0.0482 |

**Nhận xét:** 🎯 **BM25 xuất hiện!** Keyword "Phong" match trực tiếp entry title. BM25 result đứng #1 với score cao nhất (0.0482 vs vector 0.0315). Đây là case mà BM25 tốt hơn vector — exact keyword match.

---

### Query 5: "tôi đang làm việc ở đâu?"
```
kioku-lite search "công việc work job Techbase chán tired frustrated career" --limit 15
```

| Metric | Value |
|---|---|
| Total results | 15 |
| Sources | **vector: 15** |
| Hydrated | ✅ 15/15 |
| Has event_time | 14/15 |

**Nhận xét:** Vector search dominant. Kết quả bao gồm cả profile gốc và entry mới về "công việc nhàm chán" — agent trả lời đúng.

---

### Bonus: Entity-seeded Search (manual test)
```
kioku-lite search "con trai nhớ bà nội" --entities "Con trai" --limit 10
```

| Metric | Value |
|---|---|
| Total results | 10 |
| Sources | **bm25: 5, graph: 5** |

**Nhận xét:** 🎯 **Graph xuất hiện!** Khi có `--entities`, graph search kích hoạt, tìm memories liên quan đến "Con trai" qua KG traversal. Kết quả có cả BM25 (keyword match) và graph (relationship-based).

---

## 4. Tri-Hybrid Backend Contribution Summary

| Backend | Khi nào hoạt động | Ưu điểm | Hạn chế hiện tại |
|---|---|---|---|
| **Vector** | Luôn luôn (dominant) | Semantic understanding, bilingual, fuzzy match | Score range hẹp (0.015–0.033), khó phân biệt relevance |
| **BM25** | Khi query chứa keyword exact match | Exact keyword match → score cao nhất | Chỉ match khi keyword trùng text. Bilingual query (EN+VI) ít khi match FTS |
| **Graph** | Khi có `--entities` param | Relationship traversal, indirect connections | Agent hiếm khi truyền `--entities` → graph search ít kích hoạt |

---

## 5. Hydration (Original Text Retrieval)

| Metric | Result |
|---|---|
| Tất cả search results có full text? | ✅ **Có** |
| Text length trung bình | 500-900 chars (full original) |
| Content_hash → memory lookup | ✅ Hoạt động |

**Kết luận:** Hydration hoạt động đúng — tất cả search results đều trả về **văn bản gốc đầy đủ** (không phải snippet ngắn), giúp agent có đủ context để trả lời.

---

## 6. Agent Behavior (Sonnet)

### ✅ Tốt
- **Search trước khi trả lời** — agent luôn search DB trước khi respond
- **Query enrichment** — thêm keyword, bilingual, mood keywords
- **Save tự động** — lưu thông tin mới ngầm, không gián đoạn cuộc trò chuyện
- **Save + kg-index** — luôn đi cặp, đúng workflow
- **Trả lời từ DB** — không có chat history, vẫn nhận diện user chính xác
- **Multiple search** — khi 1 query chưa đủ, search thêm lần 2

### ⚠️ Cần cải thiện
- **Graph search ít kích hoạt** — agent không truyền `--entities` khi search → graph backend gần như không đóng góp
- **Entity naming** — agent index "Con trai" thay vì "Phong" (tên riêng) → recall("Phong") trả 0 results
- **event_time trên save** — 1/3 save mới có event_time rỗng (profile entry)
- **Vector score range hẹp** — hard to distinguish relevant vs less relevant

---

## 7. Recall & Connect Tests

### recall "Mẹ" (hops=2)
- **Connected nodes:** 11
- **Relationships:** 5 (SHARED_MOMENT_WITH, TRIGGERED_BY)
- **Source memories:** 4 (full text, hydrated)
- **Result:** ✅ Hoạt động — traversal tìm được chuỗi Mẹ → Phúc → Xung đột → Grateful

### recall "Phong"
- **Result:** ❌ 0 nodes — "Phong" không có trong KG (agent indexed "Con trai")
- **Workaround:** recall "Con trai" → 7 connected nodes, 4 memories ✅

### recall "Con trai" (hops=2)
- **Connected nodes:** 7
- **Source memories:** 4 (full text)
- **Result:** ✅ Hoạt động — tìm đúng memories về dạy con, xem phim cùng con

---

## 8. Action Items

| Priority | Issue | Solution |
|---|---|---|
| 🔴 High | Graph search ít kích hoạt vì agent không dùng `--entities` | Cập nhật SKILL.md: hướng dẫn agent extract entities từ query và truyền `--entities` |
| 🟡 Medium | Entity naming chung chung ("Con trai" thay vì "Phong") | Cập nhật SKILL.md: ưu tiên tên riêng khi index entities |
| 🟢 Low | Vector score range hẹp | Không cần fix — RRF reranking xử lý tốt khi có multiple backends |
| 🟢 Low | event_time rỗng cho profile entries | Acceptable — profile data không có mốc thời gian cụ thể |

---

## 9. Conclusion

**Tri-hybrid search hoạt động đúng thiết kế**, nhưng **chưa phát huy hết tiềm năng:**

- **Vector (dominant):** hoạt động tốt, luôn trả kết quả relevant
- **BM25:** hoạt động khi có keyword match, đặc biệt hiệu quả cho tên riêng
- **Graph:** hoạt động đúng khi triggered, nhưng agent hiếm khi trigger nó

**Overall: PASS ✅** — Agent hoạt động đúng, search trả đúng context, hydration đầy đủ, save tự động. Cần cải thiện graph activation strategy.
