# 2026-02-28 — Kioku Lite: OpenClaw Agent Setup & Profile Isolation Design

## Context

After shipping v0.1.14 (fix `connect` source_memories), the focus shifted to **deploying kioku-lite as a live OpenClaw agent** — a standalone Telegram-accessible memory assistant powered entirely by the kioku-lite CLI.

This devlog documents the full deployment: agent workspace creation, CLI installation into a PATH-restricted environment, and a critical profile isolation design decision.

---

## 1. OpenClaw Agent Creation

### What was built

A new OpenClaw agent `kioku-lite` was created with a dedicated workspace at `~/.openclaw/workspace-kioku-lite/`. The agent is wired to a new Telegram bot (`@phucnt_kioku_lite_bot`, token `8694810397:...`).

**Files created:**

| File | Purpose |
|---|---|
| `SOUL.md` | Personality, tone, core directives, save workflow |
| `TOOLS.md` | All 8 CLI commands with full examples + session start flow |
| `AGENTS.md` | Query enrichment rules, decision tree, group chat policy |
| `USER.md` | User profile (Phúc, timezone, preferences) |
| `IDENTITY.md` | Agent name: Kioku Lite, emoji: 🧠 |
| `HEARTBEAT.md` | Keepalive stub |

**`~/.openclaw/openclaw.json` additions:**

```json
// agents.list:
{"id": "kioku-lite", "name": "Kioku Lite Agent", "workspace": "~/.openclaw/workspace-kioku-lite",
 "model": {"primary": "anthropic/claude-haiku-4-5-20251001", "fallbacks": ["anthropic/claude-sonnet-4-5"]}}

// channels.telegram.accounts:
"kioku-lite": {"name": "Kioku Lite Bot", "dmPolicy": "pairing",
               "botToken": "8694810397:AAF7j1PMyj1cJkPYneZDkXKXBbxRhbNnryE",
               "groupPolicy": "allowlist", "streamMode": "partial"}

// bindings:
{"agentId": "kioku-lite", "match": {"channel": "telegram", "accountId": "kioku-lite"}}
```

---

## 2. CLI Installation: PATH Isolation Problem

### Problem

The OpenClaw gateway runs as a macOS LaunchAgent with a restricted PATH:

```
/Users/phucnt/.omnara/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
```

This PATH does **NOT** include:
- `~/.local/bin` (where `uv tool install` places tools)
- Any project `.venv/bin`

When the agent tried `kioku-lite save "..."` it got `command not found`.

### Solution

**Step 1:** Install kioku-lite as a proper global `uv` tool:

```bash
uv tool install "/Users/phucnt/kioku-workspace/kioku-agent-kit-lite[cli]"
# → Installs to: ~/.local/share/uv/tools/kioku-lite/
# → Symlinks to: ~/.local/bin/kioku-lite
```

**Step 2:** Add a symlink in `~/.omnara/bin` (which IS in LaunchAgent PATH):

```bash
ln -sf ~/.local/bin/kioku-lite ~/.omnara/bin/kioku-lite
```

**Result:** LaunchAgent can now resolve `kioku-lite` → `~/.omnara/bin/kioku-lite` → `~/.local/bin/kioku-lite` → `~/.local/share/uv/tools/kioku-lite/bin/kioku-lite`.

### Why `uv tool install` over direct venv symlink

Previously a direct `.venv/bin/kioku-lite` symlink was tried. `uv tool install` is better because:
- Isolated from the project's development venv
- Won't break when the dev venv is recreated
- Follows standard tool installation semantics

---

## 3. Dual-Save Architecture: Markdown + SQLite

### Design

When the agent saves a memory, it performs **two actions simultaneously**:

1. **Write Markdown to `memory/`** — plain-text backup for operator inspection and emergency restore
2. **Call `kioku-lite save`** — stores to SQLite (BM25 + vector + KG)

This was initially misidentified as a bug (why is the agent writing markdown files?). It is **intentional** — the markdown folder is the source-of-truth fallback if the SQLite database is corrupted or needs manual inspection.

**`SOUL.md` directive (added):**
```
Khi lưu ký ức: Luôn thực hiện đồng thời 2 bước:
1. Lưu file Markdown vào `memory/` (backup)
2. Gọi `kioku-lite save` để lưu vào SQLite database
```

**`AGENTS.md` architecture note (added):**
```
MEMORY ARCHITECTURE:
- memory/ folder = Markdown backup — source of truth dự phòng
- Kioku Lite CLI = database chính — tất cả search/recall/connect đều qua CLI
```

---

## 4. Profile Isolation Design: Bot ID = Profile ID

### Problem: Test Data Contamination

During development, `pytest` was run against the active kioku-lite CLI profile (`personal`). This polluted the `personal` profile with 26+ test entries, mixing them with 3 real user memories.

### Root Cause

The `personal` profile is the default profile used by kioku-lite CLI when no `--use <id>` flag is passed. The agent's instructions originally said `--use personal` (copied from dev instructions). This created a **single failure point**: any developer running CLI tests against the default profile would corrupt the agent's live data.

### Fix: Profile Per Bot

**Design principle:** Every Telegram bot (or Slack bot, etc.) gets its own isolated profile. The profile name is the **bot's numeric ID** — not a human-readable name — to ensure traceability and avoid collisions.

```
Bot: @phucnt_kioku_lite_bot
Telegram Bot ID: 8694810397
Profile name: 8694810397
```

**Rationale:**
- `8694810397` is globally unique and stable (unlike human-readable names)
- Developer never runs tests against a numeric ID like this by accident
- Easy to audit: if you see `8694810397` in a test run, it's obviously wrong
- Scales to multiple bots/channels without naming conflicts

### Migration Steps

```bash
# Create new profile
kioku-lite users --create 8694810397

# Migrate 3 real memories (INSERT with named columns to handle schema)
sqlite3 ~/.kioku-lite/users/8694810397/data/kioku.db "INSERT INTO memories ..."  # × 3

# Regenerate KG (can't copy vector store — vec0 extension not available in plain sqlite3)
kioku-lite users --use 8694810397
kioku-lite kg-index <hash1> --entities '[...]' --relationships '[...]'  # × 3

# Delete contaminated profiles
kioku-lite users --delete personal
kioku-lite users --delete fix-test
```

**Note:** Vector embeddings are regenerated lazily on next search — no data loss, but first search after migration triggers re-embedding.

### Agent Instructions Updated

All workspace files (`TOOLS.md`, `AGENTS.md`) updated:

```bash
# Session start — bước 3a: verify profile
kioku-lite users
# If active_profile != 8694810397:
kioku-lite users --use 8694810397
# Then: load context
kioku-lite search "Nguyễn Trọng Phúc profile background goals recent" --limit 10
```

---

## 5. Query Enrichment Rule (AGENTS.md)

Added a mandatory enrichment table to prevent agents from searching with raw user queries:

| User nói | ❌ Search trực tiếp | ✅ Sau khi enrich |
|---|---|---|
| "bạn biết gì về tôi" | `"tôi ai"` | `"Nguyễn Trọng Phúc profile gia đình công việc sở thích"` |
| "Hùng là ai?" | `"Hùng"` | `"Hùng người công việc sếp đồng nghiệp"` |
| "X liên quan Y?" | search | `connect "X" "Y"` |

---

## 6. Verified Working State

After all fixes, the agent was verified via Telegram session log:

```
[Session log excerpt]
kioku-lite users --use 8694810397       ✅
kioku-lite save "TechBase interview..."  ✅ → hash abc...
kioku-lite kg-index abc... --entities '[{"name":"TBV","type":"ORGANIZATION"}]'  ✅
kioku-lite search "Phúc TBV BrSE công việc"  ✅ → tri-hybrid results
```

3 memories successfully stored and searchable:
- TechBase Vietnam interview 2022 (PERSON: Hùng, ORG: TBV)
- Reading journey 2020 (CONCEPT: reading, sách)
- Career journey 2019-2024 (ORG: TBV, TOOL: kioku-lite)

---

## Summary

| Area | Status |
|---|---|
| OpenClaw agent workspace | ✅ Created |
| Telegram bot wired | ✅ `8694810397` |
| CLI accessible in LaunchAgent | ✅ `uv tool install` + symlink |
| Dual-save (markdown + SQLite) | ✅ Documented, working |
| Profile isolation (bot ID) | ✅ `8694810397` profile active |
| Test data contamination | ✅ Cleaned, old profiles deleted |
| Query enrichment rules | ✅ In AGENTS.md |
| 3 real memories migrated | ✅ KG re-indexed |
