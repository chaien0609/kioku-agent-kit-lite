# Setup Guide: Kioku Lite for an OpenClaw Agent

> For an OpenClaw agent that already has the basic workspace and chatbot (Telegram or otherwise) running.
> Hand this file to the OpenClaw **developer agent (Claude Code)** — it will execute all steps autonomously.

---

## Prerequisites (already done)

- OpenClaw gateway is running (`openclaw gateway status` → active)
- At least one agent workspace exists (e.g., `~/.openclaw/workspace-<name>/`)
- A chatbot is bound to the agent (Telegram or other channel)

---

## Step 1 — Install kioku-lite CLI

Install as a global tool so it works from LaunchAgent PATH:

```bash
# Recommended: uv tool (cleanest, no venv needed)
uv tool install "kioku-lite[cli]"

# Alternative: pipx
pipx install "kioku-lite[cli]"
```

Verify:

```bash
kioku-lite --help
```

### Fix PATH for OpenClaw LaunchAgent (macOS)

The OpenClaw LaunchAgent (background service) runs with a restricted PATH — `~/.local/bin` (where pipx/uv tool installs binaries) is usually excluded. You need to symlink `kioku-lite` into a directory that the LaunchAgent can see.

**Step 1: Find the LaunchAgent PATH**

OpenClaw installs itself under `~/.omnara/` (legacy name from when it was called Omnara). Check if that directory exists:

```bash
ls ~/.omnara/bin/
```

If it exists, symlink there:

```bash
ln -sf "$(which kioku-lite)" ~/.omnara/bin/kioku-lite

# Verify:
env -i PATH="/Users/$USER/.omnara/bin:/opt/homebrew/bin:/usr/bin:/bin" kioku-lite --help
```

If `~/.omnara/bin` does NOT exist, find the correct directory from gateway logs:

```bash
# Find which PATH the LaunchAgent actually uses:
cat ~/Library/LaunchAgents/com.omnara.*.plist 2>/dev/null | grep -A2 "PATH"
# or check existing symlinks in known locations:
ls ~/.openclaw/bin/ 2>/dev/null
```


---

## Step 2 — Pre-download Embedding Model (Recommended)

The model (~1.1 GB) auto-downloads on first use. Pre-download to avoid slow first response:

```bash
kioku-lite setup
```

---

## Step 3 — Create a Profile for the Bot

**Rule:** Each bot gets its own isolated profile. Use the **Telegram Bot ID** (integer) as the profile name — it's stable, unique, and never changes.

```bash
# Get Bot ID if you don't have it:
# curl https://api.telegram.org/bot<TOKEN>/getMe | python3 -m json.tool | grep '"id"'

kioku-lite users --create <BOT_ID>
kioku-lite users --use <BOT_ID>

# Verify:
kioku-lite users   # active_profile should be <BOT_ID>
```

> **Why use Bot ID?** Stable unique identifier, never changes, easy to audit in logs, scales cleanly when you have multiple bots. Keep it separate from `personal` or `test-*` profiles.

---

## Step 4 — Install Workspace Files

Choose the profile that matches the agent's persona, then run:

```bash
# Emotional Companion persona
kioku-lite install-openclaw companion ~/.openclaw/workspace-<name>

# OR: Business & Career Mentor persona
kioku-lite install-openclaw mentor ~/.openclaw/workspace-<name>
```

This copies pre-built **`SOUL.md`** and **`TOOLS.md`** into the workspace:

| File | What it provides |
|---|---|
| `SOUL.md` | Persona, memory directives, tone, language handling |
| `TOOLS.md` | Full CLI reference, entity schema, session start protocol, decision tree |

After running, **open `TOOLS.md`** in the workspace and replace:
- `<BOT_ID>` → the actual Telegram Bot ID (integer)
- `<UserName>` → the user's name (for context loading at session start)

> **Note on existing SOUL.md:** If the workspace already has a `SOUL.md` with a custom persona, the command will overwrite it. Backup first if needed:
> ```bash
> cp ~/.openclaw/workspace-<name>/SOUL.md ~/.openclaw/workspace-<name>/SOUL.md.bak
> ```

---

## Step 5 — Reload the Agent

Restart the OpenClaw gateway to pick up workspace changes:

```bash
openclaw gateway restart

# Verify:
openclaw gateway status
```

---

## Step 6 — Verify

Open the chatbot and send a test message. The agent should:

1. On session start: check `kioku-lite users` → activate `<BOT_ID>` if needed → load context
2. When you share info: `save` + `kg-index` immediately
3. When you ask: enrich → `search` / `recall` / `connect`

Quick test — send: `"I just had an amazing bowl of ramen for lunch."` → agent should save it and respond warmly (companion) or analytically (mentor).

---

## Profile Isolation: Dev vs Production

| Environment | Profile name | When to use |
|---|---|---|
| Production (live bot) | `<BOT_ID>` (integer) | Agent instructions — real user data |
| Development / testing | `test-<uuid>` or any name | Manual testing, development |

> ⚠️ Never run tests against the production profile. Always use a separate `test-*` profile when developing.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `kioku-lite: command not found` in gateway logs | LaunchAgent PATH missing `~/.local/bin` | Check symlink: `ls -la ~/.omnara/bin/kioku-lite` |
| Agent using wrong profile | `users --use` not called at session start | Check `TOOLS.md` session start section |
| Slow first response | Embedding model not pre-downloaded | Run `kioku-lite setup` |
| `No module named sqlite_vec` | Environment mismatch | Reinstall: `uv tool install "kioku-lite[cli]" --force` |

---

## Upgrade

When a new version of kioku-lite is released:

```bash
uv tool upgrade kioku-lite
# or: pipx upgrade kioku-lite

# Re-install workspace files to get updated SOUL.md + TOOLS.md:
kioku-lite install-openclaw <profile> ~/.openclaw/workspace-<name>

# Restart gateway:
openclaw gateway restart
```
