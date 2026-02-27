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

Kioku Lite là long-term personal memory engine chạy hoàn toàn local. Zero Docker, zero server. Mọi data trong SQLite. **Bạn (agent) tự extract entities → gọi `kg-index`.**

---

## 1. FIRST — Kiểm tra và cài đặt

### Bước 1.1 — Kiểm tra đã cài chưa

```bash
kioku-lite --version
```

**Nếu command không tồn tại** → cài:

```bash
# Tạo venv nếu chưa có (macOS/Linux)
python3 -m venv .venv
source .venv/bin/activate
pip install "kioku-lite[cli]"
```

**Nếu đã có .venv nhưng kioku-lite chưa trong đó:**
```bash
source .venv/bin/activate
pip install "kioku-lite[cli]"
```

### Bước 1.2 — Kiểm tra config đã tồn tại chưa

```bash
cat ~/.kioku-lite/config.env
```

**Nếu file không tồn tại** → chạy setup:
```bash
source .venv/bin/activate && kioku-lite setup --user-id personal
```

Setup sẽ:
1. Tạo `~/.kioku-lite/config.env`
2. Download embedding model `intfloat/multilingual-e5-large` (~1.1GB, **chỉ lần đầu**)

⚠️ **Download model có thể mất 2-5 phút.** Chạy xong mới tiếp tục.

### Bước 1.3 — Nếu muốn có SKILL.md hoạt động trên mọi project

```bash
source .venv/bin/activate && kioku-lite init --global
```

Tạo `~/.claude/skills/kioku-lite/SKILL.md` — Claude Code tự đọc từ bất kỳ project nào.

---

## 2. Load environment (PHẢI làm trước mỗi lệnh)

Vì mỗi bash call là isolated, **luôn dùng prefix sau:**

```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && kioku-lite <command>
```

Nếu không có `.venv` (cài global):
```bash
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && kioku-lite <command>
```

---

## 3. Các lệnh chính

| Lệnh | Khi nào dùng |
|---|---|
| `kioku-lite save "TEXT"` | User chia sẻ thông tin mới cần nhớ |
| `kioku-lite kg-index HASH …` | Ngay sau save — index entities bạn vừa extract |
| `kioku-lite search "QUERY"` | Recall, lookup context, tìm memories |
| `kioku-lite recall "ENTITY"` | Tìm tất cả memories liên quan entity đó |
| `kioku-lite entities` | Xem danh sách entities đã biết |
| `kioku-lite timeline` | Dòng thời gian memories |

---

## 4. `kioku-lite save` — Bước 1

```bash
source .venv/bin/activate && \
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && \
kioku-lite save "TEXT" --mood MOOD --tags "tag1,tag2" --event-time "YYYY-MM-DD"
```

**Output:** JSON với `content_hash` → dùng ngay cho `kg-index`.

**Rules:**
- ✅ Giữ nguyên **full original text** của user — không tóm tắt, không paraphrase
- ✅ Text dài (>300 chars) hay nhiều chủ đề → split thành nhiều `save` calls
- ✅ `--event-time` = khi sự kiện thực sự xảy ra (không phải thời gian hiện tại)
- ✅ Mood: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`
- ❌ Không thêm editorial comments — lưu thông tin thô

---

## 5. `kioku-lite kg-index` — Bước 2 (CRITICAL)

Sau mỗi `save`, bạn **phải tự extract entities** từ text rồi gọi `kg-index`:

```bash
source .venv/bin/activate && \
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && \
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Kioku Lite","type":"PROJECT"}]' \
  --relationships '[{"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"..."}]'
```

**Entity types:** `PERSON` | `PROJECT` | `PLACE` | `TOOL` | `CONCEPT` | `ORGANIZATION` | `EVENT`

**Relationship types:** `KNOWS` | `WORKS_ON` | `WORKS_AT` | `CONTRIBUTED_TO` | `USED_BY` | `LOCATED_AT` | `INVOLVES` | `MENTIONS`

**Extraction rules:**
- ✅ Tên nguyên gốc: `"Hùng"` không phải `"anh Hùng"`, `"Phúc"` không phải `"tôi"`
- ✅ Tiếng Việt → tên Việt: `"mẹ"`, `"TBV"`, `"dự án X"`
- ❌ Bỏ qua từ chung: `"team"`, `"mình"`, `"tôi"`, `"họ"`, `"chúng tôi"`
- ❌ Chỉ add relationship giữa entities được nhắc rõ ràng trong text
- ✅ Text không có entities cụ thể → bỏ qua `kg-index` là OK, không cần ép

---

## 6. `kioku-lite search` — Enrich first

**Enrich query** trước khi search: thay pronoun bằng tên thật đã biết.

```bash
# Session start — recall user profile
source .venv/bin/activate && \
export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && \
kioku-lite search "[UserName] profile background work goals recent events" --limit 10

# Person-specific recall
kioku-lite search "Hùng relationship projects meetings recent" --limit 5

# Date range
kioku-lite search "dự án Kioku milestone" --from 2026-02-01 --to 2026-02-28

# Entity + text combined
kioku-lite search "TBV roadmap planning" --entities "TBV,Phúc" --limit 10
```

---

## 7. Full workflow example

```
User: "Hôm nay tôi họp với Hùng và Lan về dự án Kioku Lite. Lan sẽ viết docs, Hùng lo infra."

─── Step 1: Save ───
kioku-lite save "Hôm nay họp với Hùng và Lan về dự án Kioku Lite. Lan sẽ viết docs, Hùng lo infra." \
  --mood work --event-time 2026-02-27
→ {"content_hash": "abc123...", "status": "ok"}

─── Step 2: Extract entities (you do this from the text) ───
Entities:  Hùng (PERSON), Lan (PERSON), Kioku Lite (PROJECT)
Relations: Hùng WORKS_ON Kioku Lite
           Lan  WORKS_ON Kioku Lite
           Hùng KNOWS Lan   (implied — họp cùng nhau)

─── Step 3: kg-index ───
kioku-lite kg-index abc123 \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Lan","type":"PERSON"},{"name":"Kioku Lite","type":"PROJECT"}]' \
  --relationships '[
    {"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"Hùng lo infra"},
    {"source":"Lan","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"Lan viết docs"}
  ]'
```

---

## 8. Decision Tree — Session Start

```
Bắt đầu conversation mới?
│
└─ Luôn search trước để load context:
   kioku-lite search "[UserName] profile background goals focus" --limit 10

User shares info / "nhớ cái này":
└─ save → kg-index

User hỏi / recall / "ai là X?" / "hôm qua làm gì?":
└─ ENRICH → search

"Chuyện gì xảy ra hôm [date]?":
└─ search "events activities [date]" --from DATE --to DATE

"Kể về X?":
└─ recall "X" --hops 2
```

**Critical rules:**
- 🚫 Never invent memories. 0 results → nói thật là không có.
- ✅ Luôn save khi user chia sẻ thông tin có giá trị — không cần đợi được yêu cầu.
- ✅ Luôn kg-index sau save nếu có entities nhận ra được.
- ✅ Enrich queries — replace "tôi/tao/mình/anh/chị" bằng tên thật bạn đã biết.

---

## 9. Data locations

```
~/.kioku-lite/
├── config.env                     # KIOKU_LITE_USER_ID, embed settings
└── users/<user_id>/
    ├── memory/                    # Markdown files (human-readable backup)
    │   └── YYYY-MM/
    │       └── <hash>.md
    └── data/
        └── kioku.db               # SQLite: FTS5 + sqlite-vec + KG graph tables
```

Default `user_id = personal`. Để tách data theo project:
```bash
# Trong .env của project
KIOKU_LITE_USER_ID=project-x
```

---

## 10. Troubleshooting

| Vấn đề | Giải pháp |
|---|---|
| `kioku-lite: command not found` | `source .venv/bin/activate` trước |
| `~/.kioku-lite/config.env` không có | Chạy `kioku-lite setup --user-id personal` |
| Search chậm lần đầu (~5s) | Embedding model đang load vào RAM — lần sau nhanh hơn |
| `sqlite-vec` error | `pip install --upgrade kioku-lite[cli]` |
| Model download bị interrupt | Chạy lại `kioku-lite setup` — tiếp tục từ đoạn bị dừng |
