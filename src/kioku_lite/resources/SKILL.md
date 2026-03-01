---
name: kioku-lite
description: >
  Local-first personal memory engine for AI agents. Zero Docker required.
  Stores memories in SQLite with tri-hybrid search (BM25 + vector + knowledge graph).
  Use when: user asks you to remember something, retrieve past context, or explore
  connections between people/events. You (the agent) handle entity extraction.
  NOT for: code execution, web search, or file operations.
---

# Kioku Lite — Agent Memory Skill

Kioku Lite is a long-term personal memory engine running fully local. Zero Docker, zero server. All data in SQLite. **You (the agent) extract entities → call `kg-index`.**

---

## Language Handling

- **Detect the user's language automatically.** Always respond in the same language the user is writing in.
- **Entity names:** Extract AS-IS in the user's original language — do NOT translate. Preserve the original wording.
- **Entity types & relation types:** ALWAYS use the predefined English labels (PERSON, EMOTION, TRIGGERED_BY, etc.).
- **Evidence & saved text:** Write in the user's original language.

```
# Examples of correct multilingual extraction:

User text (Vietnamese): "Hôm nay cãi nhau với sếp, cảm thấy rất căng thẳng"
→ entities: [{"name":"sếp","type":"PERSON"}, {"name":"Căng thẳng","type":"EMOTION"}, {"name":"Cãi nhau","type":"LIFE_EVENT"}]
→ relationships: [{"source":"Căng thẳng","rel_type":"TRIGGERED_BY","target":"Cãi nhau"}]

User text (English): "Had an argument with my boss, feeling very stressed"
→ entities: [{"name":"boss","type":"PERSON"}, {"name":"Stress","type":"EMOTION"}, {"name":"Argument with boss","type":"LIFE_EVENT"}]
→ relationships: [{"source":"Stress","rel_type":"TRIGGERED_BY","target":"Argument with boss"}]
```

---

## 1. FIRST — Check and Install

### Step 1.1 — Check if already installed

```bash
kioku-lite --help
```

**If the command is not found**, install via `pipx` (recommended — global, no venv needed):

```bash
pipx install "kioku-lite[cli]"
```

If `pipx` is not available:
```bash
pip install pipx && pipx ensurepath
# Restart terminal, then run pipx install again
```

Or install inside a project venv:
```bash
source .venv/bin/activate && pip install "kioku-lite[cli]"
```

### Step 1.2 — (Optional) Pre-download embedding model

Kioku Lite auto-downloads the model on first use (~1.1GB). To pre-download:

```bash
kioku-lite setup
```

**All settings have sensible defaults** — skip this if you don't mind waiting on first run.

### Step 1.3 — Inject SKILL.md for your agent

Choose **one** of these to let your AI agent discover kioku-lite:

**Option A — Global (recommended):** Run once, works in ALL projects
```bash
kioku-lite init --global
# Creates: ~/.claude/skills/kioku-lite/SKILL.md
```

**Option B — Per-project:** Active only in this project
```bash
cd /path/to/project
kioku-lite init
# Creates: ./AGENTS.md + ./.agents/skills/kioku-lite/SKILL.md
```

Choose **global** if you want Kioku Lite as your persistent personal memory engine.
Choose **per-project** if you want isolation per project.

---

## 2. SESSION START — At the beginning of every session

**At the start of every session**, you MUST:

**Step A — List profiles:**
```bash
kioku-lite users
```

Example output:
```json
{
  "profiles": [
    {"user_id": "personal", "active": true,  "has_data": true,  "db_size_kb": 512},
    {"user_id": "work",     "active": false, "has_data": false, "db_size_kb": 0}
  ],
  "active_profile": "personal",
  "hint": "Run 'kioku-lite users --use <user_id>' to switch profiles"
}
```

**Step B — Ask the user which profile to use:**

> "🗣️ Kioku Lite has these profiles:
> 1. `personal` ✓ active (512 KB)
> 2. `work` (empty)
> Which profile would you like to use? Or create a new one?"

To **create a new profile**:
```bash
kioku-lite users --create <name>
kioku-lite users --use <name>
```

**Step C — Activate and load context:**
```bash
# Activate profile (writes to ~/.kioku-lite/.active_user)
kioku-lite users --use <profile_name>

# All subsequent commands automatically use this profile
kioku-lite search "profile background goals recent" --limit 10
```

**Note:** `users --use` only needs to be called once per session. Then call `save`/`search` normally.

---

## 3. Running Commands

After installation, call directly — no export or activation needed:

```bash
kioku-lite save "text"
kioku-lite search "query"
```

If installed via venv (not pipx), activate first:
```bash
source .venv/bin/activate && kioku-lite save "text"
```

---

## 4. Core Commands

| Command | When to use |
|---|---|
| `kioku-lite save "TEXT"` | User shares new information |
| `kioku-lite kg-index HASH …` | Right after save — index entities you extracted |
| `kioku-lite search "QUERY"` | Recall, look up context |
| `kioku-lite recall "ENTITY"` | All memories related to one entity |
| `kioku-lite entities` | View known entity list |
| `kioku-lite timeline` | Chronological memory list |

---

## 5. `kioku-lite save` — Step 1

```bash
kioku-lite save "TEXT" --mood MOOD --tags "tag1,tag2" --event-time "YYYY-MM-DD"
```

**Output:** JSON with `content_hash` → use immediately with `kg-index`.

**Rules:**
- ✅ Preserve **full original text** — do not summarize or paraphrase
- ✅ Long text (>300 chars) or multiple topics → split into multiple saves
- ✅ `--event-time` = when the event actually happened (not now)
- ✅ Mood: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`
- ❌ Do not add editorial comments — save raw information

---

## 6. `kioku-lite kg-index` — Step 2 (CRITICAL)

After each `save`, **you extract entities** then call `kg-index`:

```bash
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Alice","type":"PERSON"},{"name":"Project X","type":"PROJECT"}]' \
  --relationships '[{"source":"Alice","rel_type":"WORKS_ON","target":"Project X","evidence":"..."}]'
```

**Entity types:** `PERSON` | `PROJECT` | `PLACE` | `TOOL` | `CONCEPT` | `ORGANIZATION` | `EVENT`

**Relationship types:** `KNOWS` | `WORKS_ON` | `WORKS_AT` | `CONTRIBUTED_TO` | `USED_BY` | `LOCATED_AT` | `INVOLVES` | `MENTIONS`

> **Profile-specific types:** If a persona profile (companion/mentor) is active,
> use the entity and relationship types defined in that profile's SKILL.md INSTEAD of the generic ones above.

**Extraction rules:**
- ✅ Use original name form: `"Alice"` not `"my friend Alice"`
- ✅ Entity names in the user's original language — do NOT translate
- ❌ Skip generic words: `"team"`, `"I"`, `"they"`, `"we"`
- ❌ Only add relationships explicitly mentioned in the text
- ✅ No specific entities → skip `kg-index`

---

## 7. `kioku-lite search` — Enriched Search Workflow

**Never call search with the raw user query.** Always enrich first:

### Step 1 — Get entity list as a dictionary

```bash
kioku-lite entities --limit 50
```

Output: list of `{name, type, mention_count}` — use to map pronouns and infer context.

### Step 2 — Analyze intent and enrich query

| Case | Signal | Action |
|------|--------|--------|
| **Pronoun** | "he", "she", "it", "they" | Map → entity name from conversation context |
| **Implicit subject** | "the project", "the company", "work" | Map → specific entity currently being discussed |
| **Temporal** | "yesterday", "last week", "in March" | Map → `--from DATE --to DATE` |
| **Relational** | "friend of X", "who does X", "where is X" | Use `recall X` + `connect X Y` |
| **Thematic** | general topic with no clear entity | Use pure semantic search with domain keywords |
| **Mixed** | combination of the above | Apply all transformations |

### Step 3 — Build enriched query

**Standard template:**
```
enriched_query = [ActualEntityName] + [original_keywords] + [domain_context_keywords]
entities_param = [directly mentioned + inferred from type]
date_range    = [if temporal signal present]
```

### Step 4 — Choose the right command

```bash
# Standard: text query with optional entities
kioku-lite search "ENRICHED_QUERY" --entities "E1,E2" --limit 10

# Entity deep dive: all memories related to one entity + graph traversal
kioku-lite recall "ENTITY" --hops 2 --limit 15

# Two-entity path: explain connection between two entities
kioku-lite connect "ENTITY_A" "ENTITY_B"

# Temporal slice: memories within a date range
kioku-lite search "TOPIC keywords" --from YYYY-MM-DD --to YYYY-MM-DD

# Recent timeline: chronological view
kioku-lite timeline --limit 20
```

### Step 5 — After receiving results

- Results have `content_hash` — can be used to `kg-index` additional entities if needed
- 0 results → be honest, don't guess
- Low confidence (score < 0.02) → say "possibly related, but not certain"

---

## 8. Full Workflow Example

```
User: "Today I had a meeting with Alice and Bob about the Kioku Lite project."

─── Step 1: Save ───
kioku-lite save "Today I had a meeting with Alice and Bob about the Kioku Lite project." \
  --mood work --event-time 2026-03-01
→ {"content_hash": "abc123...", "status": "ok"}

─── Step 2: Extract entities ───
  Alice (PERSON), Bob (PERSON), Kioku Lite (PROJECT)
  Alice → WORKS_ON → Kioku Lite
  Bob   → WORKS_ON → Kioku Lite

─── Step 3: kg-index ───
kioku-lite kg-index abc123 \
  --entities '[{"name":"Alice","type":"PERSON"},{"name":"Bob","type":"PERSON"},{"name":"Kioku Lite","type":"PROJECT"}]' \
  --relationships '[
    {"source":"Alice","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"meeting about Kioku Lite"},
    {"source":"Bob","rel_type":"WORKS_ON","target":"Kioku Lite","evidence":"meeting about Kioku Lite"}
  ]'
```

---

## 9. Decision Tree — Start of Every Session

```
Starting a conversation?
└─ Always search first to load context:
   kioku-lite search "[UserName] profile background goals focus" --limit 10

User shares info / "remember this":
└─ save → kg-index

User asks / "who is X?" / "what happened yesterday?":
└─ ENRICH query → search

"What happened on [date]?":
└─ search "events" --from DATE --to DATE

"Tell me about X":
└─ recall "X" --hops 2
```

**Critical rules:**
- 🚫 Never invent memories. 0 results → be honest.
- ✅ Always save when user shares valuable information.
- ✅ Always kg-index after save if entities are present.
- ✅ Enrich queries — replace "I/me/he/she" with real names.

---

## 10. Config & Data Locations

```
~/.kioku-lite/
└── users/<user_id>/        ← default user_id = "personal"
    ├── memory/             # Markdown backup
    └── data/
        └── kioku.db        # SQLite: FTS5 + sqlite-vec + KG graph
```

**Config file `~/.kioku-lite/config.env` is optional** — only needed when:
- Changing `user_id` globally
- Switching embedding provider (e.g., ollama instead of fastembed)

To isolate data per project, add `.env` to the project directory:
```bash
echo "KIOKU_LITE_USER_ID=project-x" > .env
# Project .env overrides all other settings
```

---

## 11. Troubleshooting

| Issue | Solution |
|---|---|
| `kioku-lite: command not found` | `pipx install "kioku-lite[cli]"` or `source .venv/bin/activate` |
| Search is slow on first run (~5s) | Model warming up — faster afterward |
| Model download interrupted | Run `kioku-lite setup` again |
| `No module named sqlite_vec` | `pip install --upgrade "kioku-lite[cli]"` |
