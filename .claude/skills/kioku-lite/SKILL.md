---
name: kioku-lite
description: >
  Local-first personal memory engine for AI agents. Zero Docker required.
  Stores memories in SQLite with tri-hybrid search (BM25 + vector + knowledge graph).
  Use when: user asks you to remember something, retrieve past context, or explore
  connections between people/events. You (the agent) handle entity extraction.
  NOT for: code execution, web search, or file operations.
---

# Kioku Lite — Agent Memory Skill

Kioku Lite là long-term memory engine chạy hoàn toàn local. Không cần Docker, không cần server. Mọi data trong SQLite. **Bạn (agent) tự extract entities và gọi `kg-index`.**

---

## 1. Environment & Setup (CRITICAL FIRST STEP)

Mỗi bash tool call cần load environment:

```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && kioku-lite <command>
```

Verify trước khi dùng:
```bash
source .venv/bin/activate && kioku-lite --version
```

**Nếu `kioku-lite` chưa cài:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "kioku-agent-kit-lite[cli]"
kioku-lite setup --user-id personal
```

Lần đầu dùng, embedding model (~1.1GB) sẽ được download tự động khi gọi `save` hoặc `search`.

---

## 2. The 3 Commands — Pick the Right One

| Command | When to use |
|---|---|
| `kioku-lite save "TEXT"` | User chia sẻ thông tin mới cần lưu |
| `kioku-lite kg-index HASH …` | Ngay sau save — index entities bạn extract |
| `kioku-lite search "QUERY"` | Recall, lookup, tìm context |

---

## 3. `kioku-lite save` — Bước 1 của workflow

```bash
source .venv/bin/activate && \
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && \
kioku-lite save "TEXT" --mood MOOD --tags "tag1,tag2" --event-time "YYYY-MM-DD"
```

**Output:** JSON với `content_hash` → dùng ngay cho `kg-index`.

**Rules:**
- ✅ Giữ nguyên **full original text** của user — không tóm tắt
- ✅ Nếu text dài (>300 chars) hay nhiều chủ đề — split thành nhiều saves
- ✅ `--event-time` = khi sự kiện thực sự xảy ra (không phải hôm nay)
- ✅ Mood: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`
- ❌ Không thêm editorial comments vào text — lưu thông tin thô

---

## 4. `kioku-lite kg-index` — Bước 2 (CRITICAL)

**Bạn phải tự extract entities** từ text vừa save, rồi gọi kg-index ngay:

```bash
source .venv/bin/activate && \
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && \
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Kioku","type":"PROJECT"}]' \
  --relationships '[{"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku"}]'
```

**Entity types:** `PERSON` | `PROJECT` | `PLACE` | `TOOL` | `CONCEPT`

**Relationship types:** `KNOWS` | `WORKS_ON` | `CONTRIBUTED_TO` | `USED_BY` | `LOCATED_AT` | `MENTIONS`

**Extraction rules:**
- ✅ Dùng tên đúng nguyên gốc (`"Hùng"` không phải `"anh Hùng"`)
- ✅ Tiếng Việt thì tên Việt (`"mẹ"` không phải `"mother"`)
- ❌ Bỏ qua từ chung: `"team"`, `"mình"`, `"tôi"`, `"họ"`
- ❌ Chỉ add relationship giữa entities được đề cập rõ ràng
- ✅ Nếu không có entities rõ ràng → bỏ qua kg-index là OK

---

## 5. `kioku-lite search` — Always Enrich First

Enrich query trước khi search (thêm tên thật thay pronoun):

```bash
# General recall
source .venv/bin/activate && \
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && \
kioku-lite search "[UserName] profile background work family goals" --limit 10

# Person-specific
kioku-lite search "Hùng gặp ai hôm nay làm gì dự án" --limit 5

# With date filter
kioku-lite search "meeting roadmap" --from 2026-02-01 --to 2026-02-28
```

---

## 6. Typical Workflow (Save + KG)

```
User: "Hôm nay họp với Hùng về dự án Kioku. Rất productive."

Step 1 — Save:
  kioku-lite save "Hôm nay họp với Hùng về dự án Kioku. Rất productive." --mood work
  → {"content_hash": "abc123...", ...}

Step 2 — Extract entities (you do this):
  Text mentions: Hùng (PERSON), Kioku (PROJECT)
  Relationships: Hùng WORKS_ON Kioku

Step 3 — kg-index:
  kioku-lite kg-index abc123 \
    --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Kioku","type":"PROJECT"}]' \
    --relationships '[{"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku"}]'
```

---

## 7. Decision Tree & Session Start Pattern

```
New conversation / User request?
│
├─ Session Start
│   → kioku-lite search "[UserName] profile background goals recent events"
│
├─ User shares info → "remember this" / new context
│   → kioku-lite save "..." --mood X
│   → kg-index <hash> --entities '...' --relationships '...'
│
├─ Search / recall / "who is X?" / "what happened?"
│   → ENRICH query → kioku-lite search "enriched full query"
│
└─ "What happened on [date]?"
    → kioku-lite search "events activities" --from DATE --to DATE
```

**Critical rules:**
- **Never invent memories.** 0 results = say so honestly.
- **Always save** when user shares something meaningful — don't wait to be asked.
- **Always run kg-index** after save if entities are identifiable.
- **Enrich queries** — replace "tôi/tao/mình" with real names you know.

---

## 8. Data Locations

```
~/.kioku-lite/
├── config.env                    # KIOKU_LITE_USER_ID, etc.
└── users/<user_id>/
    ├── memory/                   # Markdown files (human-readable backup)
    └── data/
        └── kioku.db              # SQLite: FTS5 + sqlite-vec + KG graph
```
