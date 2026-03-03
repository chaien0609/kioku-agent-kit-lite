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

> **🛑 STOP — Ask the user before proceeding:**
> _"Which persona do you want for this agent — **companion** (emotional listener) or **mentor** (business & career advisor)?"_
> Do not choose a default. Wait for the user's answer before running the command below.

Navigate to the workspace directory, then run the chosen profile:

```bash
mkdir -p ~/.openclaw/workspace-<name>
cd ~/.openclaw/workspace-<name>

# Install the profile chosen by the user:
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



### 4b. Create `TOOLS.md` — from the bundled template

kioku-lite ships a ready-made TOOLS.md for each persona. The developer agent should **copy** it as the starting point:

```bash
# The template lives inside the installed package:
# kioku_lite/resources/openclaw/<persona>/TOOLS.md

# Copy it to the workspace:
cp "$(python3 -c "import kioku_lite; print(kioku_lite.__path__[0])")/resources/openclaw/<persona>/TOOLS.md" \
   ~/.openclaw/workspace-<name>/TOOLS.md
```

Then replace these placeholders in the copied file:
- `<BOT_ID>` → the workspace profile name (e.g. `my-companion`)
- `<UserName>` → the user's display name

> **Why inline content instead of path references?** OpenClaw agents read `TOOLS.md` at session start as their tool reference. They don't automatically follow file paths to read external docs. Inline content ensures the agent has everything it needs immediately.


---

## Step 5 — Create Kioku Profile

**Profile name = the workspace name** — the `<name>` part of `~/.openclaw/workspace-<name>/` that you already chose.

The OpenClaw agent cannot query its own Telegram Bot ID at runtime. Using the workspace name is the simplest solution: it's developer-controlled, unique per deployment, and already defined before this step.

```bash
# Example: workspace is ~/.openclaw/workspace-my-companion/
kioku-lite users --create my-companion
kioku-lite users --use my-companion

# Verify:
kioku-lite users
```

Also replace `<AGENT_ID>` and `<UserName>` placeholders in `TOOLS.md`.



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

1. Session start: check profile → activate workspace name if needed → load context
2. User shares info: `save` + `kg-index` immediately
3. User asks: enrich → `search` / `recall` / `connect`

Quick test: `"I just had an amazing bowl of ramen for lunch."` → agent saves and responds warmly.

---

## Profile Isolation: Dev vs Production

| Environment | Profile name | When to use |
|---|---|---|
| Production (live bot) | workspace name (e.g. `my-companion`) | Real user data |
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
