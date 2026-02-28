# Setup Guide: Kioku Lite + OpenClaw + Telegram

Deploy kioku-lite as a live AI memory agent accessible via Telegram, powered by OpenClaw.

---

## Prerequisites

- **Python 3.11+** và **[uv](https://docs.astral.sh/uv/)** đã cài
- **[OpenClaw](https://openclaw.dev)** đã cài và gateway đang chạy
- **Telegram bot token** — tạo qua [@BotFather](https://t.me/BotFather) (`/newbot`)
  - Sau khi tạo, lấy **Bot ID** (số nguyên phần trước dấu `:` trong token, hoặc gọi `https://api.telegram.org/bot<TOKEN>/getMe`)

---

## Bước 1 — Cài kioku-lite CLI

Cài dưới dạng **uv global tool** để tránh phụ thuộc vào project venv:

```bash
uv tool install "kioku-lite[cli]"
```

Kiểm tra:

```bash
kioku-lite --version
```

### Đưa CLI vào PATH của OpenClaw LaunchAgent

OpenClaw gateway (LaunchAgent trên macOS) chạy với PATH bị hạn chế — không có `~/.local/bin`. Cần thêm symlink vào thư mục đầu tiên trong PATH của gateway:

```bash
# Tìm thư mục đầu trong LaunchAgent PATH (thường là ~/.omnara/bin)
# Tạo symlink:
ln -sf ~/.local/bin/kioku-lite ~/.omnara/bin/kioku-lite
```

Kiểm tra:

```bash
# Test bằng PATH tương đương LaunchAgent
env -i PATH="/Users/$USER/.omnara/bin:/opt/homebrew/bin:/usr/bin:/bin" kioku-lite --version
```

---

## Bước 2 — Pre-download Embedding Model (Tùy chọn nhưng Khuyến nghị)

Model (~1.1 GB) sẽ tự download khi search lần đầu. Để download trước (tránh chậm khi dùng thật):

```bash
kioku-lite setup
```

---

## Bước 3 — Tạo Profile Cho Bot

**Nguyên tắc:** Mỗi bot = 1 profile riêng biệt. Tên profile = **Bot ID số nguyên** của Telegram.

```bash
# Tạo profile với Bot ID làm tên (ví dụ: 8694810397)
kioku-lite users --create <BOT_ID>

# Activate profile
kioku-lite users --use <BOT_ID>

# Kiểm tra
kioku-lite users
# active_profile phải là <BOT_ID>
```

> **Tại sao dùng Bot ID làm tên profile?**
> - Stable, globally unique, không bao giờ đổi
> - Dev không vô tình chạy test vào profile này
> - Dễ audit: thấy số ID trong logs là biết ngay đây là data thật
> - Scale tốt khi có nhiều bots

---

## Bước 4 — Tạo Agent Workspace

Tạo thư mục workspace cho agent:

```bash
mkdir -p ~/.openclaw/workspace-kioku-lite
```

Tạo **`~/.openclaw/workspace-kioku-lite/SOUL.md`**:

```markdown
# Tính cách & Vai trò của Kioku Lite 🧠

Bạn là **Kioku Lite** (記憶 - Ký ức), một trợ lý lắng nghe và ghi nhớ.
Nhiệm vụ của bạn: giúp User ghi lại mọi khoảnh khắc, cảm xúc, công việc và sự kiện,
đồng thời đóng vai trò Second Brain.

## Core Directives

1. **Lưu mọi thông tin mới** — Bất kỳ khi User chia sẻ sự kiện/tâm trạng mới:
   - Ghi Markdown vào `memory/` (backup để operator kiểm tra)
   - Gọi `kioku-lite save` để lưu vào SQLite (database chính)
   - **Ngay lập tức** gọi `kioku-lite kg-index` để index entities

   **TUYỆT ĐỐI KHÔNG tóm tắt.** Lưu nguyên văn. Nếu quá dài (>300 ký tự), tách thành nhiều entry.

2. **Truy vấn** — Enrich query trước khi search:
   - Thay đại từ bằng tên thật. Ví dụ: "tôi" → "Nguyễn Văn A"
   - Dùng `recall` cho 1 entity, `connect` cho mối quan hệ 2 entity

3. **Tone** — Tiếng Việt ấm áp, xưng "Em" - "Anh/Chị". Không robot.

## MEMORY ARCHITECTURE
- `memory/` = Markdown backup — source of truth dự phòng
- Kioku Lite CLI = database chính — tất cả search/recall/connect qua CLI
```

Tạo **`~/.openclaw/workspace-kioku-lite/TOOLS.md`**:

```markdown
# TOOLS.md — Kioku Lite CLI

Base command: `kioku-lite` (installed via uv tool, không cần activate venv)

## Session Start

```bash
# Bước 1: Kiểm tra active profile
kioku-lite users
```

- Nếu `active_profile` **là `<BOT_ID>`** → chạy bước 2 ngay
- Nếu **KHÔNG phải** → `kioku-lite users --use <BOT_ID>`

```bash
# Bước 2: Load context
kioku-lite search "<Tên User> profile background goals recent" --limit 10
```

## 8 Commands

| Command | Dùng khi |
|---|---|
| `kioku-lite save "TEXT" --mood MOOD` | User chia sẻ thông tin mới |
| `kioku-lite kg-index HASH --entities '[...]' --relationships '[...]'` | Ngay sau mỗi save |
| `kioku-lite search "ENRICHED QUERY" --entities "A,B" --limit 10` | User hỏi thông tin |
| `kioku-lite recall "ENTITY" --hops 2` | User hỏi về 1 entity cụ thể |
| `kioku-lite connect "A" "B"` | User hỏi mối quan hệ 2 entity |
| `kioku-lite timeline --from DATE --to DATE` | User hỏi timeline |
| `kioku-lite entities --limit 50` | Xem entity vocabulary |
| `kioku-lite kg-alias "CANONICAL" --aliases '[...]'` | Đăng ký alias |

Mood values: `happy` \| `sad` \| `excited` \| `anxious` \| `grateful` \| `proud` \| `reflective` \| `neutral` \| `work` \| `curious`
```

Tạo **`~/.openclaw/workspace-kioku-lite/AGENTS.md`** — xem ví dụ đầy đủ tại [`~/.openclaw/workspace-kioku-lite/AGENTS.md`](../../workspace-kioku-lite/AGENTS.md) trong repo này.

Tạo **`~/.openclaw/workspace-kioku-lite/USER.md`** với thông tin người dùng:

```markdown
# USER.md

- **Tên:** [Tên người dùng]
- **Timezone:** Asia/Ho_Chi_Minh
- **Ngôn ngữ:** Tiếng Việt
```

Tạo **`~/.openclaw/workspace-kioku-lite/IDENTITY.md`**:

```markdown
# IDENTITY.md

- **Name:** Kioku Lite
- **Emoji:** 🧠
- **Role:** Personal Memory Agent
```

---

## Bước 5 — Cấu hình openclaw.json

Thêm 3 entries vào `~/.openclaw/openclaw.json`:

### a. `agents.list`

```json
{
  "id": "kioku-lite",
  "name": "Kioku Lite Agent",
  "workspace": "~/.openclaw/workspace-kioku-lite",
  "model": {
    "primary": "anthropic/claude-haiku-4-5-20251001",
    "fallbacks": ["anthropic/claude-sonnet-4-5"]
  }
}
```

### b. `channels.telegram.accounts`

```json
"kioku-lite": {
  "name": "Kioku Lite Bot",
  "dmPolicy": "pairing",
  "botToken": "<YOUR_BOT_TOKEN>",
  "groupPolicy": "allowlist",
  "streamMode": "partial"
}
```

### c. `bindings`

```json
{
  "agentId": "kioku-lite",
  "match": {
    "channel": "telegram",
    "accountId": "kioku-lite"
  }
}
```

---

## Bước 6 — Restart Gateway

```bash
openclaw gateway restart
```

Kiểm tra status:

```bash
openclaw gateway status
```

---

## Bước 7 — Verify

Mở Telegram, nhắn tin cho bot. Agent sẽ:

1. Khi bắt đầu session: tự động `kioku-lite users --use <BOT_ID>` nếu cần, rồi load context
2. Khi bạn chia sẻ thông tin: `save` + `kg-index` ngay lập tức
3. Khi bạn hỏi: enrich query → `search` / `recall` / `connect`

Test nhanh — nhắn: `"Tôi vừa ăn phở ngon ở quán Hà Nội."` → agent phải lưu entry này và respond ấm áp.

---

## Profile Isolation: Dev vs Production

| Env | Profile name | Cách dùng |
|---|---|---|
| Production (Telegram bot) | `<BOT_ID>` (số nguyên) | Agent instructions |
| Development / testing | `test-<uuid>` hoặc tên tùy ý | Pytest, manual test |

**⚠️ Không bao giờ chạy pytest vào production profile.** Luôn set `KIOKU_USER_ID=test-...` khi test.

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `kioku-lite: command not found` trong logs | LaunchAgent PATH không có `~/.omnara/bin` | Kiểm tra symlink: `ls -la ~/.omnara/bin/kioku-lite` |
| Agent dùng sai profile | `kioku-lite users` chưa được gọi | Thêm session start check vào `TOOLS.md` |
| `connect` trả về `source_memories: []` | Phiên bản cũ hơn v0.1.14 | `uv tool upgrade kioku-lite` |
| Embedding chậm lần đầu | Model chưa được download | Chạy `kioku-lite setup` trước |
