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

**Nếu lệnh không tồn tại** → cài bằng `pipx` (recommended — global, không cần venv):

```bash
pipx install "kioku-lite[cli]"
```

Nếu chưa có `pipx`:
```bash
pip install pipx && pipx ensurepath
# Restart terminal, rồi chạy lại pipx install
```

Hoặc cài trong venv của project:
```bash
source .venv/bin/activate && pip install "kioku-lite[cli]"
```

### Bước 1.2 — (Tùy chọn) Pre-download embedding model

Kioku-lite tự download model khi dùng lần đầu (~1.1GB). Nếu muốn download trước:

```bash
kioku-lite setup
```

**Tất cả settings đều có defaults hợp lý** — không cần setup nếu không ngại chờ lần đầu.

### Bước 1.3 — Init SKILL.md cho agent

Chọn **một trong hai cách** để Claude Code biết dùng kioku-lite:

**Option A — Global (recommended):** Chỉ cần làm 1 lần, tốt đời mọi project
```bash
kioku-lite init --global
# Tạo: ~/.claude/skills/kioku-lite/SKILL.md
```

**Option B — Per-project:** Chỉ active ở project này
```bash
cd /path/to/project
kioku-lite init
# Tạo: ./CLAUDE.md + ./.claude/skills/kioku-lite/SKILL.md
```

Chọn **global nếu** bạn muốn Kioku Lite là personal memory engine theo suốt (recommend).
Chọn **per-project nếu** chỉ muốn dùng cho project đó, không ảnh hưởng project khác.

---

## 2. SESSION START — Bắt đầu mỗi phiên

**Ở đầu mỗi session**, bạn MUST hỏi user muốn dùng danh tính nào:

> "🗣️ Bạn muốn dùng Kioku với danh tính nào hôm nay?
> • `personal` (mặc định — ký ức cá nhân)
> • `work` (công việc)
> • Hoặc tên khác bạn muốn?"

Sau khi user trả lời, **dùng `KIOKU_LITE_USER_ID=<id>` prefix cho mọi lệnh** trong session:

```bash
# User chọn "personal"
kioku-lite search "profile background goals" --limit 10

# User chọn "work"
KIOKU_LITE_USER_ID=work kioku-lite search "profile background goals" --limit 10

# Nếu "personal" (mặc định) thì không cần prefix
```

**Lý do hỏi mỗi session:** User có thể có nhiều profile (cá nhân, công ty, project). Data hoàn toàn tách biệt giữa các `user_id`.

---

## 3. Chạy lệnh

Sau khi cài, gọi thẳng — không cần export, không cần activate:

```bash
kioku-lite save "text"
kioku-lite search "query"
```

Nếu cài qua venv (không phải pipx), cần activate trước:
```bash
source .venv/bin/activate && kioku-lite save "text"
```

---

## 3. Các lệnh chính

| Lệnh | Khi nào dùng |
|---|---|
| `kioku-lite save "TEXT"` | User chia sẻ thông tin mới |
| `kioku-lite kg-index HASH …` | Ngay sau save — index entities bạn extract |
| `kioku-lite search "QUERY"` | Recall, lookup context |
| `kioku-lite recall "ENTITY"` | Tất cả memories liên quan một entity |
| `kioku-lite entities` | Xem danh sách entities đã biết |
| `kioku-lite timeline` | Dòng thời gian memories |

---

## 4. `kioku-lite save` — Bước 1

```bash
kioku-lite save "TEXT" --mood MOOD --tags "tag1,tag2" --event-time "YYYY-MM-DD"
```

**Output:** JSON với `content_hash` → dùng ngay cho `kg-index`.

**Rules:**
- ✅ Giữ nguyên **full original text** — không tóm tắt, không paraphrase
- ✅ Text dài (>300 chars) hay nhiều chủ đề → split thành nhiều saves
- ✅ `--event-time` = khi sự kiện thực sự xảy ra (không phải bây giờ)
- ✅ Mood: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`
- ❌ Không thêm editorial comments — lưu thông tin thô

---

## 5. `kioku-lite kg-index` — Bước 2 (CRITICAL)

Sau mỗi `save`, bạn **tự extract entities** rồi gọi `kg-index`:

```bash
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Kioku Lite","type":"PROJECT"}]' \
  --relationships '[{"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"..."}]'
```

**Entity types:** `PERSON` | `PROJECT` | `PLACE` | `TOOL` | `CONCEPT` | `ORGANIZATION` | `EVENT`

**Relationship types:** `KNOWS` | `WORKS_ON` | `WORKS_AT` | `CONTRIBUTED_TO` | `USED_BY` | `LOCATED_AT` | `INVOLVES` | `MENTIONS`

**Extraction rules:**
- ✅ Tên nguyên gốc: `"Hùng"` không phải `"anh Hùng"`
- ✅ Tiếng Việt → tên Việt: `"mẹ"`, `"TBV"`, `"dự án X"`
- ❌ Bỏ qua từ chung: `"team"`, `"mình"`, `"tôi"`, `"họ"`, `"chúng tôi"`
- ❌ Chỉ add relationship được nhắc rõ trong text
- ✅ Không có entities cụ thể → không cần gọi `kg-index`

---

## 6. `kioku-lite search` — Enrich first

Enrich query: thay pronoun bằng tên thật đã biết.

```bash
# Session start — recall user profile
kioku-lite search "[UserName] profile background work goals recent events" --limit 10

# Person-specific
kioku-lite search "Hùng relationship projects meetings recent" --limit 5

# Date range
kioku-lite search "dự án Kioku milestone" --from 2026-02-01 --to 2026-02-28

# Entity hint → boost KG recall
kioku-lite search "TBV roadmap planning" --entities "TBV,Phúc" --limit 10
```

---

## 7. Full workflow example

```
User: "Hôm nay tôi họp với Hùng và Lan về dự án Kioku Lite."

─── Step 1: Save ───
kioku-lite save "Hôm nay họp với Hùng và Lan về dự án Kioku Lite." \
  --mood work --event-time 2026-02-27
→ {"content_hash": "abc123...", "status": "ok"}

─── Step 2: Extract entities ───
  Hùng (PERSON), Lan (PERSON), Kioku Lite (PROJECT)
  Hùng → WORKS_ON → Kioku Lite
  Lan  → WORKS_ON → Kioku Lite

─── Step 3: kg-index ───
kioku-lite kg-index abc123 \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Lan","type":"PERSON"},{"name":"Kioku Lite","type":"PROJECT"}]' \
  --relationships '[
    {"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"họp về Kioku Lite"},
    {"source":"Lan","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"họp về Kioku Lite"}
  ]'
```

---

## 8. Decision Tree — Start of every session

```
Bắt đầu conversation?
└─ Luôn search trước để load context:
   kioku-lite search "[UserName] profile background goals focus" --limit 10

User shares info / "nhớ cái này":
└─ save → kg-index

User hỏi / "ai là X?" / "hôm qua làm gì?":
└─ ENRICH query → search

"Chuyện gì ngày [date]?":
└─ search "events" --from DATE --to DATE

"Kể về X":
└─ recall "X" --hops 2
```

**Critical rules:**
- 🚫 Never invent memories. 0 results → nói thật.
- ✅ Luôn save khi user chia sẻ thông tin có giá trị.
- ✅ Luôn kg-index sau save nếu có entities.
- ✅ Enrich queries — replace "tôi/mình/anh/chị" bằng tên thật.

---

## 9. Config & Data locations

```
~/.kioku-lite/
└── users/<user_id>/        ← default user_id = "personal"
    ├── memory/             # Markdown backup
    └── data/
        └── kioku.db        # SQLite: FTS5 + sqlite-vec + KG graph
```

**Config file `~/.kioku-lite/config.env` là tùy chọn** — chỉ cần khi:
- Muốn đổi `user_id` toàn cục
- Muốn dùng embedding provider khác (ollama thay fastembed)

Muốn tách data theo project → thêm `.env` vào project directory:
```bash
echo "KIOKU_LITE_USER_ID=project-x" > .env
# Project .env override mọi setting khác
```

---

## 10. Troubleshooting

| Vấn đề | Giải pháp |
|---|---|
| `kioku-lite: command not found` | `pipx install "kioku-lite[cli]"` hoặc `source .venv/bin/activate` |
| `user_id = default` (không phải `personal`) | Chạy `kioku-lite setup --user-id personal` |
| Search chậm lần đầu (~5s) | Model đang warm up — lần sau nhanh hơn |
| Download model bị interrupt | Chạy lại `kioku-lite setup` |
| `No module named sqlite_vec` | `pip install --upgrade "kioku-lite[cli]"` |
