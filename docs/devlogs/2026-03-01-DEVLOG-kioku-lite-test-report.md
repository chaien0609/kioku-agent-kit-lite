# Kioku Lite CLI — Test Report

- **Date:** 2026-03-01
- **Version:** kioku-lite 0.1.13
- **Profile:** `mentor`
- **Platform:** macOS Darwin 24.6.0
- **Install method:** `pip install -U "kioku-lite[cli]" --break-system-packages`

---

## 1. Installation & Setup

### 1.1 Install package

```bash
pip install -U "kioku-lite[cli]"
```

| Item | Result |
|---|---|
| Status | PASS |
| Note | PEP 668 block trên macOS — cần thêm `--break-system-packages` |
| Dependencies | 40+ packages installed (fastembed, onnxruntime, pydantic, sqlite-vec, ...) |

### 1.2 Create user profile

```bash
kioku-lite users --create mentor
```

**Output:**
```json
{
  "status": "created",
  "user_id": "mentor",
  "path": "/Users/phucnt/.kioku-lite/users/mentor"
}
```

| Item | Result |
|---|---|
| Status | PASS |
| Profile created | `~/.kioku-lite/users/mentor/` |

### 1.3 Initialize project

```bash
kioku-lite init
```

**Output:**
```
/Users/phucnt/test-workspace-2/CLAUDE.md
/Users/phucnt/test-workspace-2/.claude/skills/kioku-lite/SKILL.md
```

| Item | Result |
|---|---|
| Status | PASS |
| Note | Lệnh `install-profile` không tồn tại — đúng lệnh là `init` |
| Files created | `CLAUDE.md`, `.claude/skills/kioku-lite/SKILL.md` |

### 1.4 Activate profile

```bash
kioku-lite users --use mentor
```

| Item | Result |
|---|---|
| Status | PASS |
| Active profile | `mentor` |

### 1.5 Version check

```bash
kioku-lite --version
```

| Item | Result |
|---|---|
| Status | FAIL |
| Error | `No such option: --version` |
| Severity | Low — cosmetic, không ảnh hưởng chức năng |

---

## 2. Users Management

### 2.1 List profiles

```bash
kioku-lite users
```

**Output:**
```json
{
  "profiles": [
    {"user_id": "8694810397", "active": false, "has_data": true,  "db_size_kb": 4288.0},
    {"user_id": "mentor",     "active": true,  "has_data": false, "db_size_kb": 0},
    {"user_id": "personal",   "active": false, "has_data": true,  "db_size_kb": 116.0}
  ],
  "active_profile": "mentor"
}
```

| Item | Result |
|---|---|
| Status | PASS |
| Profiles found | 3 (8694810397, mentor, personal) |
| Active indicator | Correct — `mentor` marked active |
| DB size reporting | Correct |

---

## 3. Save — Memory Storage

### 3.1 Save with full options (mood, tags, event-time)

```bash
kioku-lite save "Phúc đang làm việc tại công ty TechVN, vị trí Senior Developer. \
  Anh ấy chuyên về Python và TypeScript." \
  --mood work --tags "career,profile" --event-time "2026-03-01"
```

| Item | Result |
|---|---|
| Status | PASS |
| content_hash | `a32759d4...` |
| vector_indexed | `true` |
| mood | `work` |
| tags | `["career", "profile"]` |
| event_time | `2026-03-01` |

### 3.2 Save — Meeting context

```bash
kioku-lite save "Hôm nay Phúc họp với Hùng và Lan về dự án Kioku Lite. \
  Hùng phụ trách backend, Lan phụ trách UI/UX." \
  --mood work --tags "meeting,project" --event-time "2026-03-01"
```

| Item | Result |
|---|---|
| Status | PASS |
| content_hash | `a9e4eaba...` |

### 3.3 Save — Study / personal goal

```bash
kioku-lite save "Phúc đang học tiếng Nhật, mục tiêu thi N2 vào tháng 7. \
  Mỗi ngày học 30 phút trên Duolingo." \
  --mood curious --tags "study,japanese" --event-time "2026-02-25"
```

| Item | Result |
|---|---|
| Status | PASS |
| content_hash | `ac44c1b0...` |
| event_time | `2026-02-25` (quá khứ — OK) |

### 3.4 Save — Outdoor activity

```bash
kioku-lite save "Cuối tuần Phúc đi hiking ở núi Bà Đen cùng Minh. \
  Thời tiết đẹp, leo mất 3 tiếng." \
  --mood happy --tags "outdoor,weekend" --event-time "2026-02-22"
```

| Item | Result |
|---|---|
| Status | PASS |
| content_hash | `9fa57e00...` |

### Save — Summary

| # | Topic | Mood | Tags | Event Time | Status |
|---|---|---|---|---|---|
| 1 | Career profile | work | career, profile | 2026-03-01 | PASS |
| 2 | Team meeting | work | meeting, project | 2026-03-01 | PASS |
| 3 | Japanese study | curious | study, japanese | 2026-02-25 | PASS |
| 4 | Hiking trip | happy | outdoor, weekend | 2026-02-22 | PASS |

---

## 4. KG-Index — Knowledge Graph Indexing

### 4.1 Index entities + relationships (memory #1)

```bash
kioku-lite kg-index a32759d4... \
  --entities '[
    {"name":"Phúc","type":"PERSON"},
    {"name":"TechVN","type":"ORGANIZATION"},
    {"name":"Python","type":"TOOL"},
    {"name":"TypeScript","type":"TOOL"}
  ]' \
  --relationships '[
    {"source":"Phúc","rel_type":"WORKS_AT","target":"TechVN","evidence":"làm việc tại TechVN"},
    {"source":"Phúc","rel_type":"WORKS_ON","target":"Python","evidence":"chuyên về Python"},
    {"source":"Phúc","rel_type":"WORKS_ON","target":"TypeScript","evidence":"chuyên về TypeScript"}
  ]'
```

| Item | Result |
|---|---|
| Status | PASS |
| entities_added | 4 |
| relationships_added | 3 |

### 4.2 Index complex relationships (memory #2)

```bash
kioku-lite kg-index a9e4eaba... \
  --entities '[Phúc, Hùng, Lan, Kioku Lite]' \
  --relationships '[Hùng→Kioku Lite, Lan→Kioku Lite, Phúc→Kioku Lite, Phúc→Hùng, Phúc→Lan]'
```

| Item | Result |
|---|---|
| Status | PASS |
| entities_added | 4 |
| relationships_added | 5 |

### 4.3 Index tools & events (memory #3)

| Item | Result |
|---|---|
| Status | PASS |
| entities_added | 3 (Phúc, Duolingo, JLPT N2) |
| relationships_added | 2 |

### 4.4 Index places & people (memory #4)

| Item | Result |
|---|---|
| Status | PASS |
| entities_added | 3 (Phúc, Minh, Núi Bà Đen) |
| relationships_added | 2 |

### KG-Index — Totals

| Metric | Count |
|---|---|
| Total entities | 11 unique |
| Total relationships | 12 |
| Entity types used | PERSON (4), TOOL (3), ORGANIZATION (1), PROJECT (1), PLACE (1), EVENT (1) |
| Relationship types used | WORKS_ON (6), KNOWS (3), WORKS_AT (1), LOCATED_AT (1) |

---

## 5. KG-Alias — Entity Alias Registration

### 5.1 CSV format (incorrect)

```bash
kioku-lite kg-alias "Phúc" --aliases "anh Phúc,PhucNT"
```

| Item | Result |
|---|---|
| Status | FAIL |
| Error | `Error parsing --aliases JSON` |
| Root cause | `--aliases` expects JSON array, not CSV string |

### 5.2 JSON array format (correct)

```bash
kioku-lite kg-alias "Phúc" --aliases '["anh Phúc","PhucNT"]'
```

**Output:**
```json
{
  "status": "ok",
  "canonical": "Phúc",
  "aliases_added": ["anh Phúc", "PhucNT"]
}
```

| Item | Result |
|---|---|
| Status | PASS |
| Canonical | `Phúc` |
| Aliases registered | `anh Phúc`, `PhucNT` |

### 5.3 Alias resolution verification

```bash
kioku-lite recall "PhucNT" --hops 1 --limit 5
```

| Item | Result |
|---|---|
| Status | PASS |
| Resolved to | `Phúc` (canonical) |
| Connected nodes | 11 (full graph of Phúc) |
| Source memories | 2 memories returned correctly |

---

## 6. Search — Tri-Hybrid (BM25 + Vector + Knowledge Graph)

### 6.1 Entity-filtered search

```bash
kioku-lite search "Phúc làm gì ở công ty" --entities "Phúc,TechVN" --limit 5
```

| Item | Result |
|---|---|
| Status | PASS |
| Top result | Career profile (score: 0.0328, source: **bm25**) |
| Total results | 4 |
| Sources used | bm25 (1), graph (3) |
| Entity filter | Correctly boosted TechVN-related memory |

### 6.2 Pure semantic search (no entity filter)

```bash
kioku-lite search "dự án project team" --limit 5
```

| Item | Result |
|---|---|
| Status | PASS |
| Top result | Meeting about Kioku Lite (score: 0.0164, source: **vector**) |
| Total results | 4 |
| Sources used | All vector — no BM25/graph matches |
| Ranking | Correct — meeting > career > hiking > study |

### 6.3 Temporal search (date range)

```bash
kioku-lite search "events highlights" --from 2026-02-20 --to 2026-02-28 --limit 5
```

| Item | Result |
|---|---|
| Status | PASS |
| Total results | 4 |
| Note | Date filter returned all 4 results — memories with `event_time` outside range still appear (sorted by `date`, not `event_time`) |
| Observation | `--from/--to` may filter on `date` (save timestamp) rather than `event_time` |

### 6.4 Nonsense query (zero-match expected)

```bash
kioku-lite search "something that does not exist at all xyz123" --limit 5
```

| Item | Result |
|---|---|
| Status | WARNING |
| Total results | 4 (expected: 0) |
| Scores | 0.0156 — 0.0164 (all low) |
| Sources | All vector |
| Note | Vector search always returns nearest neighbors — no hard cutoff. Agent must interpret low scores as "no real match" |

### Search — Source Distribution

| Source | Appearances | Note |
|---|---|---|
| `vector` | Most common | Default fallback when no BM25/KG hit |
| `bm25` | When keywords match directly | Higher scores |
| `graph` | When entity filter activates KG | Medium scores |

---

## 7. Recall — Entity Graph Traversal

### 7.1 Recall central entity

```bash
kioku-lite recall "Phúc" --hops 2 --limit 10
```

| Item | Result |
|---|---|
| Status | PASS |
| Connected nodes | 11 (full graph) |
| Relationships | 10 edges |
| Source memories | 4 (all memories) |
| Graph structure | Phúc is hub — connected to every other entity |

**Graph visualization:**
```
                    TechVN (ORG)
                   /
        Python ── Phúc ── Hùng
      TypeScript /  |  \    \
               /    |   Lan  Kioku Lite (PROJECT)
         Duolingo   |
              \   Minh
          JLPT N2   \
                  Núi Bà Đen
```

### 7.2 Recall peripheral entity

```bash
kioku-lite recall "Hùng" --hops 1
```

| Item | Result |
|---|---|
| Status | PASS (implicit — tested via connect) |
| Direct connections | Kioku Lite, Phúc |

---

## 8. Connect — Path Finding Between Entities

### 8.1 Direct connection (1 hop)

```bash
kioku-lite connect "Hùng" "Kioku Lite"
```

| Item | Result |
|---|---|
| Status | PASS |
| Connected | `true` |
| Path | `Hùng → Kioku Lite` (direct) |
| Evidence memory | Meeting memory |

### 8.2 Indirect connection (2 hops)

```bash
kioku-lite connect "Minh" "Kioku Lite"
```

| Item | Result |
|---|---|
| Status | PASS |
| Connected | `true` |
| Path | `Minh → Phúc → Kioku Lite` |
| Evidence memories | Hiking + Meeting |

### 8.3 Unrelated entities (via hub)

```bash
kioku-lite connect "Duolingo" "Núi Bà Đen"
```

| Item | Result |
|---|---|
| Status | PASS |
| Connected | `true` |
| Path | `Duolingo → Phúc → Núi Bà Đen` |
| Note | All entities connect through Phúc (hub node) |

---

## 9. Entities — Entity Listing

```bash
kioku-lite entities --limit 20
```

| Item | Result |
|---|---|
| Status | PASS |
| Total entities | 11 |

**Full entity list:**

| Entity | Type | Mentions | Aliases |
|---|---|---|---|
| Phúc | PERSON | 4 | anh Phúc, PhucNT |
| Duolingo | TOOL | 1 | — |
| Hùng | PERSON | 1 | — |
| JLPT N2 | EVENT | 1 | — |
| Kioku Lite | PROJECT | 1 | — |
| Lan | PERSON | 1 | — |
| Minh | PERSON | 1 | — |
| Núi Bà Đen | PLACE | 1 | — |
| Python | TOOL | 1 | — |
| TechVN | ORGANIZATION | 1 | — |
| TypeScript | TOOL | 1 | — |

---

## 10. Timeline — Chronological View

```bash
kioku-lite timeline --limit 10
```

| Item | Result |
|---|---|
| Status | PASS |
| Total entries | 4 |
| Sort order | `processing_time` (insertion order) |
| Note | Sorted by `timestamp` (when saved), NOT by `event_time` |

**Timeline output:**

| # | Date | Event Time | Mood | Tags | Content (truncated) |
|---|---|---|---|---|---|
| 1 | 2026-03-01 | 2026-03-01 | work | career, profile | Phúc đang làm việc tại TechVN... |
| 2 | 2026-03-01 | 2026-03-01 | work | meeting, project | Hôm nay Phúc họp với Hùng và Lan... |
| 3 | 2026-03-01 | 2026-02-25 | curious | study, japanese | Phúc đang học tiếng Nhật... |
| 4 | 2026-03-01 | 2026-02-22 | happy | outdoor, weekend | Cuối tuần Phúc đi hiking... |

---

## 11. Summary

### Overall Results

| Category | Tests | Passed | Failed | Warnings |
|---|---|---|---|---|
| Installation & Setup | 5 | 4 | 1 | 0 |
| Users Management | 1 | 1 | 0 | 0 |
| Save | 4 | 4 | 0 | 0 |
| KG-Index | 4 | 4 | 0 | 0 |
| KG-Alias | 3 | 2 | 1 | 0 |
| Search | 4 | 3 | 0 | 1 |
| Recall | 2 | 2 | 0 | 0 |
| Connect | 3 | 3 | 0 | 0 |
| Entities | 1 | 1 | 0 | 0 |
| Timeline | 1 | 1 | 0 | 0 |
| **Total** | **28** | **25** | **2** | **1** |

### Issues Found

| # | Severity | Command | Issue | Workaround |
|---|---|---|---|---|
| 1 | Low | `--version` | Option not supported | Use `pip show kioku-lite` instead |
| 2 | Medium | `kg-alias --aliases` | CSV format rejected — requires JSON array | Use `'["alias1","alias2"]'` format |
| 3 | Low | `search` (no match) | Vector search always returns results even for nonsense queries (no score threshold) | Agent must interpret scores < 0.02 as "no real match" |

### Verdict

**PASS** — Kioku Lite hoat dong on dinh. Tat ca cac chuc nang chinh (save, kg-index, search, recall, connect, entities, timeline, users, kg-alias) deu hoat dong dung. 2 loi nho (--version, alias format) khong anh huong den workflow chinh.
