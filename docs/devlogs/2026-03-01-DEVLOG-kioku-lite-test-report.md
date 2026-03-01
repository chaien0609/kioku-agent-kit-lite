# Devlog: Kioku Lite — Agent Profile Setup & CLI Test

**Date:** 2026-03-01  
**Version tested:** 0.1.13 (cài bằng `install-profile` feature mới là 0.1.14)

---

## Bối cảnh

Ngày hôm nay kép hai mục tiêu:
1. **Thiết kế hệ thống Agent Profile** cho Kioku Lite (companion, mentor) theo chuẩn Agent Skills.
2. **Test toàn diện CLI** với Claude Code trên máy mới (test-workspace).

---

## Thay đổi chính

### Agent Profile System
Kioku Lite giờ có thêm thư mục `src/kioku_lite/resources/profiles/`:
- `companion/` — Bạn tâm sự, schema tập trung: `EMOTION`, `LIFE_EVENT`, `TRIGGERED_BY`.
- `mentor/` — Cố vấn công việc, schema tập trung: `DECISION`, `LESSON_LEARNED`, `LED_TO_LESSON`.

Mỗi profile gồm 2 file đã viết sẵn hoàn chỉnh (`AGENTS.md` + `SKILL.md`), có thể deploy ngay bằng:

```bash
kioku-lite install-profile companion   # hoặc: mentor
```

Lệnh này tự động copy `SKILL.md` vào `~/.agents/skills/kioku-companion/` và `AGENTS.md` ra thư mục hiện tại — không cần hard-code path, không cần script bash, Agent không cần tự generate gì cả.

### Bug fix: `kioku-lite init` tạo AGENTS.md thay vì CLAUDE.md
Phiên bản cũ của `init` tạo `CLAUDE.md` và cài Skill vào `.claude/skills/` (hardcode cho Claude Code). Đã fix lại theo chuẩn open standard:
- `CLAUDE.md` → `AGENTS.md`
- `.claude/skills/kioku-lite/` → `.agents/skills/kioku-lite/`

Tương thích với Claude Code, Cursor, Windsurf và bất kỳ agent nào hỗ trợ chuẩn AGENTS.md.

---

## Kết quả test CLI (Claude Code)

**25/28 tests PASS.** Toàn bộ core workflows (save, kg-index, search, recall, connect, entities, timeline, users, kg-alias) hoạt động đúng.

**2 issues nhỏ không đáng lo:**

| Issue | Mô tả | Tại sao không đáng lo |
|---|---|---|
| `--version` không có | `kioku-lite --version` báo lỗi | Đây là tính năng cosmetic thuần túy. Dùng `pip show kioku-lite` thay thế. Không ảnh hưởng bất kỳ workflow memory nào. |
| `kg-alias --aliases` từ chối CSV | `"alias1,alias2"` bị reject, phải dùng JSON `'["alias1","alias2"]'` | Đây là **hành vi đúng và có chủ ý** — `--aliases` nhận JSON để nhất quán với `--entities` và `--relationships`. Claude Code lần đầu thử nhầm format, nhưng sau đó tự sửa và PASS. Agent có đủ khả năng tự học format đúng. |

**1 warning về semantic search:** Vector search luôn trả về kết quả dù query vô nghĩa (nearest-neighbor không có hard threshold). Agent cần tự nhận biết score < 0.02 là "không có match thực sự" — đã được ghi chú trong `SKILL.md`.

---

## Next steps

- [ ] Bump version lên 0.1.15 + publish PyPI với lệnh `install-profile` và fix AGENTS.md.
