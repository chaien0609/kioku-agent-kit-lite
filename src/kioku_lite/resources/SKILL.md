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

## 1. Language Handling

- **Detect the user's language automatically.** Always respond in the same language the user is writing in.
- **Entity names:** Extract AS-IS in the user's original language — do NOT translate.
- **Entity types & relation types:** ALWAYS use the predefined English labels (PERSON, EMOTION, TRIGGERED_BY, etc.).
- **Evidence & saved text:** Write in the user's original language.

```
Example (Vietnamese):
  "Hôm nay cãi nhau với sếp, cảm thấy rất căng thẳng"
  → entities: [{"name":"sếp","type":"PERSON"}, {"name":"Căng thẳng","type":"EMOTION"}]
  → relationships: [{"source":"Căng thẳng","rel_type":"TRIGGERED_BY","target":"Cãi nhau","evidence":"cãi nhau với sếp, cảm thấy rất căng thẳng"}]

Example (English):
  "Had an argument with my boss, feeling very stressed"
  → entities: [{"name":"boss","type":"PERSON"}, {"name":"Stress","type":"EMOTION"}]
  → relationships: [{"source":"Stress","rel_type":"TRIGGERED_BY","target":"Argument with boss","evidence":"had an argument with my boss, feeling very stressed"}]
```

---

## 2. Installation & Setup

### Check if installed
```bash
kioku-lite --help
```

### Install (if not found)
```bash
pipx install "kioku-lite[cli]"        # Global — recommended
# OR: pip install "kioku-lite[cli]"   # Inside a venv
```

### (Optional) Pre-download embedding model (~1.1GB)
```bash
kioku-lite setup
```

### Inject SKILL.md for agent discovery
```bash
kioku-lite init --global   # Global: works in ALL projects
# OR: kioku-lite init      # Per-project: creates ./AGENTS.md + .agents/skills/
```

---

## 3. Session Start — Run EVERY Session

**Step A — Check active profile:**
```bash
kioku-lite users
```

**Step B — Ask user which profile to use** (if multiple exist), then activate:
```bash
kioku-lite users --use <profile_name>
# To create a new profile: kioku-lite users --create <name>
```

**Step C — Load context:**
```bash
kioku-lite search "profile background goals recent" --limit 10
```

> `users --use` only needs to run once per session. All subsequent commands use it automatically.

---

## 4. Command Reference

| Command | When to use |
|---|---|
| `kioku-lite save "TEXT" --mood MOOD --event-time YYYY-MM-DD` | User shares new information |
| `kioku-lite kg-index HASH --entities '[…]' --relationships '[…]' --event-time YYYY-MM-DD` | Right after save — index entities you extracted |
| `kioku-lite search "QUERY" --entities "E1,E2" --limit 10` | Recall, look up context |
| `kioku-lite recall "ENTITY" --hops 2 --limit 15` | All memories + graph around one entity |
| `kioku-lite connect "A" "B"` | Explain relationship between two entities |
| `kioku-lite entities --limit 50` | View known entity vocabulary |
| `kioku-lite timeline --limit 20` | Chronological memory list |
| `kioku-lite kg-alias "CANONICAL" --aliases '["alias1"]'` | Register entity aliases (SAME_AS) |

---

## 5. `save` — Store a Memory

```bash
kioku-lite save "TEXT" --mood MOOD --tags "tag1,tag2" --event-time "YYYY-MM-DD"
```

**Output:** JSON with `content_hash` → use immediately with `kg-index`.

**Rules:**
- ✅ Preserve **full original text** — do not summarize or paraphrase
- ✅ **`--event-time` is REQUIRED** whenever the event is not today. Search filters use this field.
  Parse relative dates: "hồi tháng 3 năm ngoái" → `2025-03-01`, "yesterday" → yesterday's date, "năm 2019" → `2019-01-01`. Omit only if the event is happening today or timing is truly unclear.
- ✅ Use the **same `--event-time`** on both `save` AND `kg-index` for consistency.
- ✅ Mood values: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`
- ❌ Do not add editorial comments — save raw information

### Entry Splitting Strategy

**SPLIT into multiple entries if ANY of these are true:**
- ≥3 distinct topics (e.g. career + family + hobbies)
- ≥10 entities would be needed in `kg-index`
- ≥2 time phases with different contexts (e.g. "worked in Japan 5 years, then moved back")
- \>300 words AND covers multiple topics

**Keep as 1 entry if ALL of these are true:**
- Single topic with single emotional arc
- <5 entities total
- Single time point or tight narrative

**How to split:** Group by phase → topic → emotion. Each entry should have 5–8 focused entities.

```
❌ BAD: 1 mega-entry (1500 words, 28 entities, 14 topics)
   → KG becomes tangled, search returns noise

✅ GOOD: 14 focused entries (~100-150 words, 5-8 entities each)
   → Clean KG, each entry is independently searchable
   → Use relationships to LINK entries across topics
```

---

## 6. `kg-index` — Index Entities & Relationships

After **every** `save`, you must: (1) disambiguate, (2) extract, (3) index.

### Step 1 — Disambiguate: check existing entities

```bash
kioku-lite entities --limit 50
```

Compare extracted names against the returned list. **Reuse existing canonical names** instead of creating duplicates:
- If `"Phúc"` exists with 12 mentions, use `"Phúc"` — not `"anh Phúc"` or `"Nguyễn Trọng Phúc"`
- If `"TechBase Vietnam"` exists, use it — not `"TBV"` or `"công ty"`
- For true aliases, register them: `kioku-lite kg-alias "Phúc" --aliases '["anh Phúc","Nguyễn Trọng Phúc"]'`

### Step 2 — Extract entities & relationships from the saved text

**Entity types (generic):** `PERSON` | `PROJECT` | `PLACE` | `TOOL` | `CONCEPT` | `ORGANIZATION` | `EVENT`

**Relationship types (generic):** `KNOWS` | `WORKS_ON` | `WORKS_AT` | `CONTRIBUTED_TO` | `USED_BY` | `LOCATED_AT` | `INVOLVES` | `MENTIONS`

> **Profile-specific types:** If a persona profile (companion/mentor) is active, use the entity & relationship types from that profile's SKILL.md INSTEAD of the generic ones above.

**Extraction rules:**
- ✅ Use short, canonical name form: `"Alice"` not `"my friend Alice"`
- ✅ Entity names in the user's original language — do NOT translate
- ✅ `evidence` = **exact quote** from the saved text that supports the relationship
- ❌ Skip generic words: `"I"`, `"we"`, `"they"`, `"team"`, `"everyone"`
- ❌ Only add relationships explicitly stated in the text — do NOT infer
- ✅ No specific entities → skip `kg-index` entirely

### Step 3 — Call `kg-index` with `--event-time`

```bash
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Alice","type":"PERSON"},{"name":"Project X","type":"PROJECT"}]' \
  --relationships '[
    {"source":"Alice","rel_type":"WORKS_ON","target":"Project X","evidence":"had a meeting with Alice about Project X"}
  ]' \
  --event-time "2024-06-15"
```

**`--event-time` is critical for temporal accuracy.** It sets the date on graph edges.

Parse relative time expressions to YYYY-MM-DD relative to today's date:
| Expression | Today = 2026-03-03 | Result |
|---|---|---|
| "hôm qua" / "yesterday" | | `2026-03-02` |
| "tuần trước" / "last week" | | `2026-02-24` |
| "tháng 3 năm ngoái" / "last March" | | `2025-03-01` |
| "năm 2019" / "in 2019" | | `2019-01-01` |
| "lúc 22 tuổi" (user born 1993) | | `2015-01-01` |
| Today or unclear | | Omit `--event-time` (defaults to today) |

---

## 7. `search` — Enriched Search Workflow

**Never call search with the raw user query.** Always enrich first.

### Step 1 — Analyze intent and enrich

| Signal | Action |
|---|---|
| Pronouns: "he", "she", "it" | Replace with entity name from context |
| Implicit subject: "the project" | Map to specific entity name |
| Temporal: "yesterday", "last month" | Add `--from DATE --to DATE` |
| Relational: "who does X work with?" | Use `recall "X"` or `connect "X" "Y"` |
| Thematic: general topic query | Use semantic search with domain keywords |

### Step 2 — Build and run enriched query

```bash
# Standard search (with entity boost)
kioku-lite search "Alice Project X meeting outcomes" --entities "Alice,Project X" --limit 10

# Entity deep dive (graph traversal)
kioku-lite recall "Alice" --hops 2 --limit 15

# Connection between two entities
kioku-lite connect "Alice" "Bob"

# Temporal slice
kioku-lite search "events" --from 2026-02-01 --to 2026-02-28

# Recent timeline
kioku-lite timeline --limit 20
```

### Step 3 — Interpret results

- Results contain `content_hash` — can be used for additional `kg-index` if needed
- 0 results → be honest, don't invent memories
- Low confidence (score < 0.02) → say "possibly related, but not certain"

---

## 8. Full Workflow Example

```
User: "Năm 2019, tôi quyết định quay lại đọc sách nghiêm túc."

─── Step 1: Save ───
kioku-lite save "Năm 2019, tôi quyết định quay lại đọc sách nghiêm túc." \
  --mood reflective --event-time 2019-01-01
→ {"content_hash": "a1b2c3..."}

─── Step 2: Disambiguate ───
kioku-lite entities --limit 50
→ Check: "Phúc" exists (12 mentions) — reuse it

─── Step 3: Extract & Index ───
kioku-lite kg-index a1b2c3 \
  --entities '[{"name":"Phúc","type":"PERSON"},{"name":"Đọc sách","type":"COPING_MECHANISM"},{"name":"Quyết định quay lại đọc sách","type":"LIFE_EVENT"}]' \
  --relationships '[
    {"source":"Phúc","rel_type":"TRIGGERED_BY","target":"Quyết định quay lại đọc sách","evidence":"quyết định quay lại đọc sách nghiêm túc"},
    {"source":"Quyết định quay lại đọc sách","rel_type":"REDUCED_BY","target":"Đọc sách","evidence":"quay lại đọc sách nghiêm túc"}
  ]' \
  --event-time 2019-01-01
```

---

## 9. Decision Tree

```
Session start?
└─ users → search to load context

User shares info / "remember this":
└─ Check splitting criteria → save (split if needed)
   → entities (disambiguate) → extract → kg-index each

User asks a question:
└─ ENRICH query → search / recall / connect

"What happened on [date]?":
└─ search --from DATE --to DATE

"Tell me about X":
└─ recall "X" --hops 2
```

**Critical rules:**
- 🚫 Never invent memories. 0 results → be honest.
- ✅ Always `save` when user shares valuable information.
- ✅ Always `kg-index` after `save` if entities are present (with `--event-time`!).
- ✅ Always disambiguate against existing entities before indexing.
- ✅ Enrich queries — replace pronouns with real entity names.

---

## 10. Config & Data Locations

```
~/.kioku-lite/
└── users/<user_id>/        ← default user_id = "personal"
    ├── memory/             # Markdown backup (source of truth)
    └── data/
        └── kioku.db        # SQLite: FTS5 + sqlite-vec + KG tables
```

Optional `~/.kioku-lite/config.env` — only needed to change embedding provider or default user_id.
Per-project override: `echo "KIOKU_LITE_USER_ID=project-x" > .env`

---

## 11. Troubleshooting

| Issue | Solution |
|---|---|
| `kioku-lite: command not found` | `pipx install "kioku-lite[cli]"` or `source .venv/bin/activate` |
| Search is slow on first run (~5s) | Model warming up — faster afterward |
| Model download interrupted | Run `kioku-lite setup` again |
| `No module named sqlite_vec` | `pip install --upgrade "kioku-lite[cli]"` |
