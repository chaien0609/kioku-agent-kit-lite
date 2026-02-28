# Test Log: Enriched Search & Session Management

**Ngày:** 2026-02-28  
**Tester:** Claude Code (Opus 4.5)  
**Versions tested:** 0.1.10 → 0.1.11 → 0.1.12 → 0.1.13  
**Profile:** personal  
**Environment:** macOS Darwin 25.1.0, Python 3.13.4, pipx

---

## 1. Bugs Found & Fixed

### BUG-01 — BM25 Search Always Returns 0 Results
**Version found:** 0.1.10  
**Fixed:** 0.1.11  
**Severity:** High (P1)

**Root cause:**  
`search_fts()` trong `memory_store.py` wrap toàn bộ query với dấu ngoặc kép → FTS5 phrase search.  
Query "Techbase Việt Nam TBV BrSE 2019" phải match đúng phrase đó trong content → 0 results.

```python
# Before (0.1.10) — phrase match, fail với multi-word
safe_query = '"' + query.replace('"', '""') + '"'

# After (0.1.11) — term match, mỗi từ search độc lập
tokens = query.strip().split()
safe_tokens = ['"' + t.replace('"', '""') + '"' for t in tokens if t]
safe_query = " ".join(safe_tokens)
```

**Verification:**  
- "Techbase Việt Nam TBV BrSE 2019" → `source: "bm25"` xuất hiện trong results ✅
- Query pronoun sau enrich → bm25 + graph mixed sources ✅

---

### BUG-02 — content_hash Missing from Search/Recall/Timeline Output
**Version found:** 0.1.10  
**Fixed:** 0.1.11  
**Severity:** High (P0)

**Root cause:**  
`search_memories()` trong `service.py` hydrate nội dung đúng (call `get_by_hashes()`),  
nhưng không include `content_hash` trong output dict → agent mất reference để `kg-index` memory cũ.

**Fix:** Add `"content_hash": r.content_hash` vào output của:
- `search_memories()` — mỗi result item
- `recall_entity()` — mỗi `source_memories` item  
- `get_timeline()` — mỗi entry (thêm `content_hash` vào query SQL)

**Verification:**
```json
{
  "content": "Phúc đang build kioku-lite...",
  "source": "bm25",
  "content_hash": "15db370db4e8e0ed2bc87f16b2a684b51e80d6beabf98822bff0cad1a1bc705f"
}
```
✅ `search`, `recall`, `timeline` đều có `content_hash`

---

### BUG-03 — SKILL.md Typo: `explain-connection` → `connect`
**Version found:** 0.1.12  
**Fixed:** 0.1.13  
**Severity:** Medium (doc bug)

SKILL.md section 6 dùng `kioku-lite explain-connection` (3 chỗ),  
nhưng CLI command thực tế là `kioku-lite connect`.

**Locations fixed:**
- Line 210: bảng query type → action
- Line 248: example transformation
- Line 271: bước 4 command reference

**Verification:** `kioku-lite --help | grep connect` → `connect` ✅

---

### BUG-04 — Embedding Model Warning Spam
**Version found:** 0.1.10  
**Fixed:** 0.1.11  
**Severity:** Low (P2)

FastEmbed thay đổi pooling từ CLS → mean, output warning mỗi lần chạy.  
Không ảnh hưởng functionality nhưng noise trong output.

**Fix:**
```python
warnings.filterwarnings("ignore", message=".*mean pooling.*CLS embedding.*", category=UserWarning)
```

---

## 2. Features Verified Working

### 2.1 Session Start Flow (v0.1.8+)

```bash
kioku-lite users                    # list profiles với active flag
kioku-lite users --use personal     # set active, ghi ~/.kioku-lite/.active_user
kioku-lite search "..." --limit 10  # auto dùng active profile, không cần prefix
```

✅ Profile isolation: `~/.kioku-lite/users/<id>/data/kioku.db`  
✅ No env var prefix needed sau `--use`

---

### 2.2 Save + KG-Index Workflow

5 memories saved thành công:

| # | Content summary | Mood | Hash prefix |
|---|-----------------|------|-------------|
| 1 | Nguyễn Trọng Phúc — thông tin cá nhân | neutral | 3a93c22a |
| 2 | Làm việc tại Nhật, vị trí BrSE | work | 021e37fb |
| 3 | Chọn TBV để tiếp tục BrSE | work | d8b564c5 |
| 4 | Học Tiếng Nhật vì "ít người học" | reflective | 863b0de3 |
| 5 | Build kioku-lite — Python + SQLite | work | 15db370d |

10 entities indexed, 7 relationships.  
✅ `content_hash` từ `save` dùng ngay cho `kg-index`

---

### 2.3 Tri-Hybrid Search Results (v0.1.11)

| Query type | Expected source | Actual |
|------------|----------------|--------|
| Semantic — "cầu nối Việt Nam Nhật Bản" | vector | ✅ vector |
| Exact keyword — "Techbase Việt Nam TBV" | bm25 | ✅ bm25 (fixed) |
| Entity-boosted — `--entities "Phúc,kioku-lite"` | graph | ✅ graph |
| Enriched pronoun — "Phúc làm gì career work" | bm25+graph | ✅ mixed |

---

### 2.4 Enriched Search Workflow (v0.1.12)

6 query cases tested:

| Case | Input | Enriched command | Result |
|------|-------|-----------------|--------|
| Pronoun | "anh ấy làm gì?" | `search "Phúc làm gì career" --entities "Phúc,kioku-lite"` | ✅ bm25 + graph |
| Implicit entity | "công ty đang làm gì?" | `search "TBV công ty work" --entities "TBV,Phúc"` | ✅ bm25 + graph |
| Type inference | "Phúc dùng tool gì?" | `search "Phúc tool build" --entities "Phúc,Python,SQLite,kioku-lite"` | ✅ bm25 + graph |
| Temporal | "2019 có gì?" | `search "events 2019" --from 2019-01-01 --to 2019-12-31` | ✅ date filtered |
| Relational | "SQLite liên quan gì đến Phúc?" | `connect "Phúc" "SQLite"` | ✅ path: Phúc→kioku-lite→SQLite |
| Alias | "techbase có gì?" | `search --entities "techbase"` | ✅ maps → TBV |

---

### 2.5 Knowledge Graph Features

```bash
kioku-lite connect "Phúc" "SQLite"
# → {"connected": true, "paths": [["Phúc", "kioku-lite", "SQLite"]]}

kioku-lite kg-alias "TBV" --aliases '["Techbase Việt Nam","techbase"]'
# → search "techbase" → canonical TBV node trong graph_context
```

✅ Multi-hop path finding (2 hops)  
✅ Alias/canonical mapping  
✅ `graph_context.evidence` trả về full original text của edge source

---

## 3. Known Limitations (Not Bugs)

| Item | Note |
|------|------|
| BM25 với pure semantic query | Expected — BM25 chỉ match keyword, vector handle semantic |
| vector 100% khi data ít (<10 memories) | Expected — vector luôn có result, BM25 cần exact token match |
| Spiderum JS URLs không load | WebFetch limitation, không liên quan kioku-lite |
| Model download lần đầu ~1.1GB | Expected, one-time |

---

## 4. Version Changelog Summary

| Version | Changes |
|---------|---------|
| 0.1.8 | `kioku-lite users` + `--use` + `.active_user` session file |
| 0.1.9 | Remove `config.env` completely, clean profile management |
| 0.1.10 | SKILL.md session start rewrite dùng `users --use` |
| **0.1.11** | **BUG FIX: BM25 term search; content_hash in all outputs; suppress fastembed warning** |
| 0.1.12 | SKILL.md Section 6: enriched search workflow (5 steps, 6 case types) |
| **0.1.13** | **BUG FIX: SKILL.md `explain-connection` → `connect` (3 occurrences)** |

---

## 5. Open Items

None. All identified bugs fixed as of v0.1.13.

---

*Log compiled from Claude Code test reports — 2026-02-28*
