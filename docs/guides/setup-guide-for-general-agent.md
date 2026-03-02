# Agent Setup Guide for Kioku Lite

> Compatible with: Claude Code, Cursor, Windsurf, and any agent supporting AGENTS.md / SKILL.md

---

## Step 1 — Install Kioku Lite CLI (once per machine)

```bash
pipx install "kioku-lite[cli]"
```

> If `pipx` is not available: `pip install pipx && pipx ensurepath` then restart your terminal.

Verify install:
```bash
kioku-lite --help
```

---

## Step 2 — Register Skill with your Agent (once per agent)

This teaches your agent **how to use** Kioku Lite across all projects:

```bash
kioku-lite init --global
```

This installs `~/.claude/skills/kioku-lite/SKILL.md` — auto-discovered by Claude Code in every project. (For Cursor/Windsurf: also run `kioku-lite init` per-project to get `.agents/skills/kioku-lite/SKILL.md`.)

After running, follow the instructions printed to the terminal to complete Step 2 (activate a workspace).

---

## Step 3 — Activate for a specific workspace

Navigate to the directory where you want to use Kioku, then choose **one option**:

### Option A — No persona (generic schema)

```bash
cd ~/your-workspace
kioku-lite init
```

Creates:
- `AGENTS.md` in current directory — tells the agent to use Kioku here
- `.agents/skills/kioku-lite/SKILL.md` — full CLI reference

### Option B — With a built-in persona (recommended)

```bash
cd ~/your-workspace
kioku-lite install-profile companion   # Emotional Companion
# OR
kioku-lite install-profile mentor      # Business & Career Mentor
```

Creates:
- `AGENTS.md` in current directory — includes Identity + Role for the persona
- `~/.agents/skills/kioku-<name>/SKILL.md` — Identity + KG Schema for the persona (CLI docs from global SKILL.md)

---

## Step 4 — Create a Kioku user profile

Each user or persona should have a separate profile to isolate data:

```bash
kioku-lite users --create mentor        # create profile
kioku-lite users --use mentor           # activate it
```

> Check status: `kioku-lite users` → lists all profiles and shows which is active.

---

## Step 5 — Open your Agent and start

```bash
claude   # or cursor, windsurf, ...
```

Say to your agent:

> **"Read AGENTS.md and the kioku-lite skill, then start a session for me."**

The agent will automatically:
1. Read `AGENTS.md` → understand its role (companion / mentor / ...)
2. Read `SKILL.md` → know how to call the CLI
3. Run `kioku-lite users` → confirm which profile is active
4. Run `kioku-lite search "..."` → load past memory context

---

## Command Reference

| Command | When to use |
|---|---|
| `pipx install "kioku-lite[cli]"` | First install on a machine |
| `kioku-lite init --global` | Once per agent (global skill registration) |
| `kioku-lite init` | Each new workspace (no persona) |
| `kioku-lite install-profile <name>` | Each new workspace (with persona) |
| `kioku-lite users --create <id>` | Each new user or persona |
| `kioku-lite users --use <id>` | Switch active profile |
| `pipx upgrade kioku-lite && kioku-lite init --global` | When a new version is released |

---

## Notes

- Available profiles: `companion` (Emotional Companion), `mentor` (Business & Career Mentor)
- Data stored at: `~/.kioku-lite/users/<profile_id>/`
- Language: The agent auto-detects and responds in the user's language. Entity names are stored in the original language; entity types always use English labels.
- To add more profiles in the future: `kioku-lite install-profile <new_name>` (if that name exists in the package)
