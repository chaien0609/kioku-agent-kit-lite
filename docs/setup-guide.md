# Hướng dẫn cài đặt Kioku Lite cho AI Agent

> Version: 0.1.16 | Tương thích: Claude Code, Cursor, Windsurf, bất kỳ agent nào hỗ trợ AGENTS.md / SKILL.md

---

## Bước 1 — Cài Kioku Lite CLI (1 lần duy nhất)

```bash
pipx install "kioku-lite[cli]"
```

> Nếu chưa có `pipx`: `pip install pipx && pipx ensurepath` rồi restart terminal.

Kiểm tra cài xong:
```bash
kioku-lite --help
```

---

## Bước 2 — Đăng ký Skill với Agent (1 lần duy nhất)

Lệnh này dạy agent biết **cách dùng** Kioku Lite trong mọi project:

```bash
kioku-lite init --global
```

Agent sẽ tự phát hiện SKILL.md từ `~/.claude/skills/kioku-lite/SKILL.md`.

---

## Bước 3 — Kích hoạt cho workspace cụ thể

Chuyển sang thư mục muốn dùng Kioku, rồi chọn **một trong hai cách**:

### Cách A — Không có persona (dùng schema mặc định)

```bash
cd ~/your-workspace
kioku-lite init
```

Tạo ra:
- `AGENTS.md` ở thư mục hiện tại — Agent đọc để biết cần dùng Kioku
- `.agents/skills/kioku-lite/SKILL.md` — Hướng dẫn CLI chi tiết

### Cách B — Với persona định sẵn (recommended)

```bash
cd ~/your-workspace
kioku-lite install-profile companion   # Bạn tâm sự
# HOẶC
kioku-lite install-profile mentor      # Cố vấn công việc
```

Tạo ra:
- `AGENTS.md` ở thư mục hiện tại — Mang Identity + vai trò cụ thể
- `~/.agents/skills/kioku-<name>/SKILL.md` — Identity + KG Schema riêng theo persona (CLI docs đọc từ global SKILL.md)

---

## Bước 4 — Tạo profile Kioku cho user

Mỗi user/persona nên có 1 profile riêng để tách dữ liệu:

```bash
kioku-lite users --create mentor        # tạo profile
kioku-lite users --use mentor           # kích hoạt
```

> Kiểm tra: `kioku-lite users` → xem danh sách và profile đang active.

---

## Bước 5 — Mở Agent và bắt đầu

```bash
claude   # hoặc cursor, windsurf, ...
```

Nói với agent:

> **"Đọc AGENTS.md và skill kioku-lite, rồi bắt đầu session cho tôi."**

Agent sẽ tự động:
1. Đọc `AGENTS.md` → nhận vai trò (companion/mentor/...)
2. Đọc SKILL.md → biết cách gọi CLI
3. Chạy `kioku-lite users` → xác nhận profile đang active
4. Chạy `kioku-lite search "..."` → load context từ memory cũ

---

## Tóm tắt lệnh

| Lệnh | Chạy khi nào |
|---|---|
| `pipx install "kioku-lite[cli]"` | Lần đầu cài máy |
| `kioku-lite init --global` | Lần đầu với agent (1 lần duy nhất) |
| `kioku-lite init` | Mỗi workspace mới (không persona) |
| `kioku-lite install-profile <name>` | Mỗi workspace mới (có persona) |
| `kioku-lite users --create <id>` | Mỗi user/persona mới |
| `kioku-lite users --use <id>` | Mỗi khi đổi user đang active |
| `pipx upgrade kioku-lite && kioku-lite init --global` | Khi có version mới |

---

## Xem thêm

- Profiles có sẵn: `companion` (Bạn tâm sự), `mentor` (Cố vấn công việc)
- Data lưu tại: `~/.kioku-lite/users/<profile_id>/`
- Thêm profile mới trong tương lai: `kioku-lite install-profile <tên_mới>` (nếu tên đó tồn tại trong package)
