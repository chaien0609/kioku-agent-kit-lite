# Setup Guide: Kioku Lite + OpenClaw + Telegram

Deploy kioku-lite as a live AI memory agent accessible via Telegram, powered by OpenClaw.

---

## Prerequisites

- **Python 3.11+** và **[uv](https://docs.astral.sh/uv/)** đã cài
- **[OpenClaw](https://openclaw.dev)** đã cài và gateway đang chạy
- **Telegram bot token** — tạo qua [@BotFather](https://t.me/BotFather) (`/newbot`)

---

## Bước 1 — Cài kioku-lite CLI

Cài dưới dạng **uv global tool** để tránh phụ thuộc vào project venv:

```bash
uv tool install "kioku-lite[cli]"
# or: pipx install "kioku-lite[cli]"
```

Kiểm tra:

```bash
kioku-lite --version
```

---

## Bước 2 — Pre-download Embedding Model (Tùy chọn nhưng Khuyến nghị)

Model (~1.1 GB) sẽ **tự động download** khi search lần đầu nếu bỏ qua bước này. Để download trước (tránh chậm khi dùng thật):

```bash
kioku-lite setup
```

---

## Bước 3 — Setup Kioku-lite Workspace

> **Dùng guide chuyên biệt cho OpenClaw:**
> → [`setup-guide-for-openclaw-agent.md`](./setup-guide-for-openclaw-agent.md)
>
> Guide đó hướng dẫn toàn bộ: cài global skill, tạo SOUL.md, TOOLS.md, tạo kioku profile, và cấu hình `openclaw.json`.

---

## Bước 4 — Cấu hình openclaw.json

Thêm 3 entries vào `~/.openclaw/openclaw.json`:

### a. `agents.list`

```json
{
  "id": "kioku-<name>",
  "name": "Kioku <Name> Agent",
  "workspace": "~/.openclaw/workspace-<name>",
  "model": {
    "primary": "anthropic/claude-haiku-4-5-20251001",
    "fallbacks": ["anthropic/claude-sonnet-4-5"]
  }
}
```

### b. `channels.telegram.accounts`

```json
"kioku-<name>": {
  "name": "Kioku <Name> Bot",
  "dmPolicy": "pairing",
  "botToken": "<YOUR_BOT_TOKEN>",
  "groupPolicy": "allowlist",
  "streamMode": "partial"
}
```

### c. `bindings`

```json
{
  "agentId": "kioku-<name>",
  "match": {
    "channel": "telegram",
    "accountId": "kioku-<name>"
  }
}
```

---

## Bước 5 — Restart Gateway

```bash
openclaw gateway restart
```

Kiểm tra status:

```bash
openclaw gateway status
```

---

## Bước 6 — Verify

Mở Telegram, nhắn tin cho bot. Agent sẽ:

1. Khi bắt đầu session: tự kiểm tra profile → load context
2. Khi bạn chia sẻ thông tin: `save` + `kg-index` ngay lập tức
3. Khi bạn hỏi: enrich query → `search` / `recall` / `connect`

Test nhanh — nhắn: `"Tôi vừa ăn phở ngon ở quán Hà Nội."` → agent phải lưu entry này và respond ấm áp.

---

## Profile Isolation: Dev vs Production

| Env | Profile name | Cách dùng |
|---|---|---|
| Production (Telegram bot) | Workspace name (e.g. `my-companion`) | Agent thực |
| Development / testing | `test-<uuid>` hoặc tên tùy ý | Pytest, manual test |

**⚠️ Không bao giờ chạy pytest vào production profile.** Luôn set `KIOKU_USER_ID=test-...` khi test.

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `kioku-lite: command not found` trong logs | CLI chưa cài hoặc PATH của gateway không thấy | Kiểm tra cài đặt: `kioku-lite --version`; xem tài liệu OpenClaw về PATH của gateway |
| Agent dùng sai profile | Profile chưa active đúng | Thêm session start check vào `TOOLS.md` |
| `connect` trả về `source_memories: []` | Phiên bản cũ hơn v0.1.14 | `uv tool upgrade kioku-lite` |
| Embedding chậm lần đầu | Model chưa được download | Chạy `kioku-lite setup` trước |
