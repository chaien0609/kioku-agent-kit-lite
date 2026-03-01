# Setup Guide: Kioku Lite for an OpenClaw Agent

> For an OpenClaw agent that already has the basic workspace and chatbot (Telegram or otherwise) running.
> Hand this file to the OpenClaw **developer agent (Claude Code)** — it will execute all steps autonomously.

---

## Prerequisites (already done)

- OpenClaw gateway is running (`openclaw gateway status` → active)
- At least one agent workspace exists (e.g., `~/.openclaw/workspace-<name>/`)
- A chatbot is bound to the agent (Telegram or other channel)
- The agent's `SOUL.md` defines the persona/purpose

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

The OpenClaw LaunchAgent runs with a restricted PATH — `~/.local/bin` is usually excluded. Add a symlink to the first directory in the LaunchAgent's PATH:

```bash
# Create symlink (adjust target path if using pipx: ~/.local/bin/kioku-lite)
ln -sf "$(which kioku-lite)" ~/.omnara/bin/kioku-lite

# Verify with LaunchAgent-equivalent PATH
env -i PATH="/Users/$USER/.omnara/bin:/opt/homebrew/bin:/usr/bin:/bin" kioku-lite --help
```

> If `~/.omnara/bin` doesn't exist, check `~/.openclaw/openclaw.json` for the `PATH` set in the gateway environment, or look at an existing working agent's symlinks.

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

## Step 4 — Update Workspace Files

Navigate to the agent's workspace (e.g., `~/.openclaw/workspace-<name>/`) and update or create these files:

### 4a. `TOOLS.md` — CLI Reference for the Agent

Replace or create `TOOLS.md` with the following content:

```markdown
# TOOLS.md — Kioku Lite CLI

**Base command:** `kioku-lite` (global install, no venv activation needed)

## Session Start — Run at the beginning of EVERY session

Step 1: Check active profile
\`\`\`bash
kioku-lite users
\`\`\`

- If `active_profile` is already `<BOT_ID>` → proceed to Step 2
- If NOT → run: `kioku-lite users --use <BOT_ID>`

> ⚠️ Profile `<BOT_ID>` contains real user data. Never switch to `personal` or other profiles during a live session.

Step 2: Load context
\`\`\`bash
kioku-lite search "<User name> profile background goals recent" --limit 10
\`\`\`

## Core Commands

| Command | When to use |
|---|---|
| `kioku-lite save "TEXT" --mood MOOD --tags "t1,t2" --event-time YYYY-MM-DD` | User shares new information |
| `kioku-lite kg-index HASH --entities '[...]' --relationships '[...]'` | Immediately after every save |
| `kioku-lite search "ENRICHED_QUERY" --entities "A,B" --limit 10` | User asks about something |
| `kioku-lite recall "ENTITY" --hops 2 --limit 15` | Deep dive on one entity |
| `kioku-lite connect "A" "B"` | Connection between two entities |
| `kioku-lite timeline --from DATE --to DATE --limit 20` | Chronological view |
| `kioku-lite entities --limit 50` | See entity vocabulary |
| `kioku-lite kg-alias "CANONICAL" --aliases '["alias1","alias2"]'` | Register aliases |

Mood values: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`

## kg-index — Entity Extraction Rules

YOU extract entities from the text — the engine does not do this automatically.

- ✅ Use exact name form: `"Alice"` not `"my friend Alice"`
- ✅ Entity names in the user's original language — do NOT translate
- ❌ Skip generic words: `"I"`, `"we"`, `"they"`, `"team"`, `"it"`
- ❌ Only add relationships explicitly stated in the text
- ✅ No specific entities → skip kg-index

Entity types: `PERSON` | `PROJECT` | `PLACE` | `TOOL` | `CONCEPT` | `ORGANIZATION` | `EVENT`
Relation types: `KNOWS` | `WORKS_ON` | `WORKS_AT` | `CONTRIBUTED_TO` | `USED_BY` | `LOCATED_AT` | `INVOLVES` | `MENTIONS`

## Search Enrichment — Always Enrich Before Searching

Never pass the raw user query to search. Always enrich first:
- Replace pronouns with real names ("I" → user's name, "he" → entity name from context)
- Add domain context keywords
- Use `--entities` for KG-focused boost

## Decision Tree

\`\`\`
Session start?
└─ Check profile → load context with search

User shares new info / "remember this":
└─ save → extract entities → kg-index

User asks a question:
└─ ENRICH query → search

User asks about one specific entity:
└─ recall "entity" --hops 2

User asks how X relates to Y:
└─ connect "X" "Y"

"What happened yesterday/last week?":
└─ timeline --from DATE --to DATE
\`\`\`

Never invent memories. 0 results → be honest.
```

### 4b. `SOUL.md` — Add Memory Directives

Add these directives to the existing `SOUL.md` (without replacing the persona):

```markdown
## Memory Directives (Kioku Lite)

1. **Save all new information** — whenever the user shares events, emotions, or facts:
   - Call `kioku-lite save` with the verbatim original text (DO NOT summarize or paraphrase)
   - If content is long (>300 chars) or multi-topic, split into separate saves
   - Immediately call `kioku-lite kg-index` after each save — this is non-negotiable

2. **Query** — always enrich before searching:
   - Replace pronouns with real names
   - Use `recall` for one entity, `connect` for relationships between two entities

3. **Language** — respond in the same language the user writes in (auto-detect).
   Entity names are stored in the user's original language. Entity types always use English labels.
```

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

Quick test — send: `"I just had an amazing bowl of ramen for lunch."` → agent should save it and respond warmly.

---

## Profile Isolation: Dev vs Production

| Environment | Profile name | When to use |
|---|---|---|
| Production (live bot) | `<BOT_ID>` (integer) | Agent instructions — real user data |
| Development / testing | `test-<uuid>` or any name | Pytest, manual dev testing |

> ⚠️ Never run tests against the production profile. Always set `KIOKU_USER_ID=test-...` or use a separate profile when developing.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `kioku-lite: command not found` in gateway logs | LaunchAgent PATH missing `~/.local/bin` | Check symlink: `ls -la ~/.omnara/bin/kioku-lite` |
| Agent using wrong profile | `users --use` not called at session start | Add profile check to `TOOLS.md` session start section |
| `connect` returns `source_memories: []` | Package older than v0.1.14 | `uv tool upgrade kioku-lite` or `pipx upgrade kioku-lite` |
| Slow first response | Embedding model not pre-downloaded | Run `kioku-lite setup` |
| `No module named sqlite_vec` | Environment mismatch | Reinstall: `uv tool install "kioku-lite[cli]" --force` |

---

## Upgrade

When a new version of kioku-lite is released:

```bash
uv tool upgrade kioku-lite
# or: pipx upgrade kioku-lite

# Re-inject SKILL.md if using global agent skills:
kioku-lite init --global
```
