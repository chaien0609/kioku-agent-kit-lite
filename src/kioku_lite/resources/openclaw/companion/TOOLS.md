# TOOLS.md — Kioku Lite CLI

**Base command:** `kioku-lite` (global install via uv tool or pipx — no venv activation needed)

> 🚨 **`kioku-lite` is your ONLY memory system.** When a user shares ANY information — stories, profile data, feelings, facts, URLs — your FIRST action is `kioku-lite save`. Do NOT use USER.md, notes, or files to store user data.

---

## Session Start — Run at the beginning of EVERY session

**Step 1: Check active profile**
```bash
kioku-lite users
```
- If `active_profile` is already `<BOT_ID>` → proceed to Step 2
- If NOT → `kioku-lite users --use <BOT_ID>`

> ⚠️ Profile `<BOT_ID>` contains real user data. Never switch to `personal` or `test-*` profiles during a live session.

**Step 2: Load context**
```bash
kioku-lite search "<UserName> profile background goals recent" --limit 10
```

---

## Core Commands

| Command | When to use |
|---|---|
| `kioku-lite save "TEXT" --mood MOOD --event-time YYYY-MM-DD` | User shares new information |
| `kioku-lite kg-index HASH --entities '[…]' --relationships '[…]' --event-time YYYY-MM-DD` | Immediately after every save |
| `kioku-lite search "ENRICHED_QUERY" --entities "A,B" --limit 10` | User asks about something |
| `kioku-lite recall "ENTITY" --hops 2 --limit 15` | Deep dive on one entity |
| `kioku-lite connect "A" "B"` | Connection between two entities |
| `kioku-lite timeline --from DATE --to DATE --limit 20` | Chronological view |
| `kioku-lite entities --limit 50` | See entity vocabulary |
| `kioku-lite kg-alias "CANONICAL" --aliases '["alias1"]'` | Register aliases |

Mood values: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`

---

## Language Handling

- **Respond in the user's language automatically** — detect from their messages.
- **Entity names:** Extract AS-IS in the user's original language — do NOT translate.
- **Entity types & relation types:** Always use English labels (see below).

---

## kg-index — 3-Step Process

### Step 1: Disambiguate — check existing entities first
```bash
kioku-lite entities --limit 50
```
Reuse existing canonical names. If `"Phúc"` exists (12 mentions), use it — not `"anh Phúc"`.
For true aliases: `kioku-lite kg-alias "Phúc" --aliases '["anh Phúc"]'`

### Step 2: Extract entities & relationships

**Companion persona schema:**
- Entity types: `PERSON` | `EMOTION` | `LIFE_EVENT` | `COPING_MECHANISM` | `PLACE`
- Relation types: `TRIGGERED_BY` | `REDUCED_BY` | `BROUGHT_JOY` | `SHARED_MOMENT_WITH` | `HAPPENED_AT`

**Rules:**
- ✅ Use short canonical name: `"Alice"` not `"my friend Alice"`
- ✅ Entity names in user's language — do NOT translate
- ✅ `evidence` = **exact quote** from the saved text supporting the relationship
- ❌ Skip generic words: `"I"`, `"we"`, `"they"`, `"team"`
- ❌ Only add relationships explicitly stated — do NOT infer

### Step 3: Call kg-index with --event-time

```bash
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Stress","type":"EMOTION"},{"name":"Argument","type":"LIFE_EVENT"}]' \
  --relationships '[{"source":"Stress","rel_type":"TRIGGERED_BY","target":"Argument","evidence":"felt stressed after the argument"}]' \
  --event-time "2026-02-15"
```

**`--event-time` is critical.** Parse relative dates to YYYY-MM-DD:
- "hôm qua" → yesterday's date
- "tuần trước" → last week
- "năm 2019" → `2019-01-01`
- Today or unclear → omit (defaults to today)

---

## Entry Splitting Strategy

**SPLIT into multiple entries if ANY:**
- ≥3 distinct topics | ≥10 entities | ≥2 time phases | >300 words + multiple topics

**Keep as 1 entry if ALL:**
- Single topic, <5 entities, single time point

**How:** Group by phase → topic → emotion. Aim for 5–8 entities per entry. Use relationships to link entries.

---

## Search Enrichment — Always Enrich Before Searching

Never pass raw user queries to search. Always enrich first:
- Replace pronouns with real entity names
- Add relevant domain/context keywords
- Use `--entities` for KG-focused boost

---

## Decision Tree

```
Session start?
└─ Check profile → load context with search

User shares new info / "remember this":
└─ Check splitting → save (split if needed) → disambiguate → extract → kg-index each (with --event-time!)

User asks a question:
└─ ENRICH query → search

User asks about one specific entity:
└─ recall "entity" --hops 2

User asks how X relates to Y:
└─ connect "X" "Y"

"What happened yesterday/last week?":
└─ timeline --from DATE --to DATE
```

Never invent memories. 0 results → be honest with the user.
