# Setup Guide: Kioku Lite for an OpenClaw Agent

> **For the OpenClaw developer agent (Claude Code).**
> OpenClaw supports the same AGENTS.md / SKILL.md open standard — run the same install commands as for any general agent, then adapt the output files into OpenClaw's workspace format.

---

## Prerequisites (already done)

- OpenClaw gateway is running (`openclaw gateway status` → active)
- An agent workspace exists or will be created (e.g., `~/.openclaw/workspace-<name>/`)
- A Telegram bot (or other chatbot) is ready to be bound

---

## Step 1 — Install kioku-lite CLI

```bash
uv tool install "kioku-lite[cli]"
# or: pipx install "kioku-lite[cli]"

kioku-lite --help   # verify
```

---

## Step 2 — Register Global Skill (once per machine)

```bash
kioku-lite init --global
```

This installs: `~/.agents/skills/kioku-lite/SKILL.md` — the full CLI reference.
OpenClaw agents will use this as the source of truth for how to call the CLI.

---

## Step 3 — Install Profile for the Workspace

Navigate to the workspace directory (or any temp dir — we just need the generated files):

```bash
mkdir -p ~/.openclaw/workspace-<name>
cd ~/.openclaw/workspace-<name>

# Choose a profile:
kioku-lite install-profile companion   # Emotional Companion
# OR
kioku-lite install-profile mentor      # Business & Career Mentor
```

This generates two files:

| File | Location | Content |
|---|---|---|
| `AGENTS.md` | `~/.openclaw/workspace-<name>/AGENTS.md` | Workspace context + persona role |
| `SKILL.md` | `~/.agents/skills/kioku-<name>/SKILL.md` | Identity + KG Schema for the persona |

---

## Step 4 — Create OpenClaw Workspace Files

OpenClaw uses a different file convention than the open standard. The developer agent should **derive** the OpenClaw-specific files from the files generated in Step 3:

### 4a. Create `SOUL.md` — from `AGENTS.md`

`AGENTS.md` already contains everything needed for `SOUL.md`: space context, agent role, memory directives, and language handling. Simply adapt its content into OpenClaw's format:

```markdown
# SOUL.md — <Agent Name>

<Paste the content of AGENTS.md here, expanded into prose paragraphs if desired>
```

> No need to pull from the profile SKILL.md — `AGENTS.md` covers persona, role, and directives completely.



### 4b. Create `TOOLS.md` — reference SKILL files by path, do NOT copy content

Create `~/.openclaw/workspace-<name>/TOOLS.md` with the following structure:

```markdown
# TOOLS.md — Kioku Lite CLI

## Session Start — Run at the beginning of EVERY session

Step 1: Verify active profile
\`\`\`bash
kioku-lite users
\`\`\`
- If `active_profile` is already `<BOT_ID>` → proceed
- If NOT → `kioku-lite users --use <BOT_ID>`

> ⚠️ Profile `<BOT_ID>` is real user data. Never switch to `personal` or `test-*` during a live session.

Step 2: Load context
\`\`\`bash
kioku-lite search "<UserName> profile background goals recent" --limit 10
\`\`\`

---

## CLI Reference

Read the full CLI documentation from:
- **Commands, search enrichment, decision tree:** `~/.agents/skills/kioku-lite/SKILL.md`
- **Identity, KG schema (entity & relation types for this persona):** `~/.agents/skills/kioku-<name>/SKILL.md`

> The KG schema in `kioku-<name>/SKILL.md` takes precedence over any generic types in the global skill.
```

**Why reference by path instead of copy-pasting?**
- Always up-to-date when `kioku-lite init --global` or `install-profile` is re-run on upgrade
- Single source of truth — no drift between TOOLS.md and the actual SKILL files
- OpenClaw agents can read files natively; referencing by path is equivalent


---

## Step 5 — Create Kioku Profile for the Bot

```bash
# Use the Telegram Bot ID as profile name (stable, unique, audit-friendly)
kioku-lite users --create <BOT_ID>
kioku-lite users --use <BOT_ID>

# Verify:
kioku-lite users
```

Also update `<BOT_ID>` and `<UserName>` placeholders in `TOOLS.md`.

---

## Step 6 — Register Agent in `openclaw.json`

Add to `~/.openclaw/openclaw.json`:

**`agents.list`:**
```json
{
  "id": "kioku-<name>",
  "name": "Kioku <Name> Agent",
  "workspace": "~/.openclaw/workspace-<name>"
}
```

**`channels.telegram.accounts`** (if using Telegram):
```json
"kioku-<name>": {
  "name": "Kioku <Name> Bot",
  "dmPolicy": "pairing",
  "botToken": "<YOUR_BOT_TOKEN>",
  "groupPolicy": "allowlist",
  "streamMode": "partial"
}
```

**`bindings`:**
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

## Step 7 — Restart Gateway

```bash
openclaw gateway restart
openclaw gateway status
```

---

## Step 8 — Verify

Open the chatbot and test. The agent should:

1. Session start: check profile → activate `<BOT_ID>` if needed → load context
2. User shares info: `save` + `kg-index` immediately
3. User asks: enrich → `search` / `recall` / `connect`

Quick test: `"I just had an amazing bowl of ramen for lunch."` → agent saves and responds warmly.

---

## Profile Isolation: Dev vs Production

| Environment | Profile name | When to use |
|---|---|---|
| Production (live bot) | `<BOT_ID>` (integer) | Real user data |
| Development / testing | `test-<uuid>` or any name | Testing only |

> ⚠️ Never test against the production profile.

---

## Upgrade

```bash
uv tool upgrade kioku-lite
# or: pipx upgrade kioku-lite

kioku-lite init --global             # refresh global SKILL.md
kioku-lite install-profile <name>    # refresh profile AGENTS.md + SKILL.md
# Then re-derive SOUL.md + TOOLS.md from updated files (Step 4)

openclaw gateway restart
```
