# TOOLS.md — Kioku Lite CLI

**Base command:** `kioku-lite` (global install via uv tool or pipx — no venv activation needed)

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
| `kioku-lite save "TEXT" --mood MOOD --tags "t1,t2" --event-time YYYY-MM-DD` | User shares new information |
| `kioku-lite kg-index HASH --entities '[...]' --relationships '[...]'` | Immediately after every save |
| `kioku-lite search "ENRICHED_QUERY" --entities "A,B" --limit 10` | User asks about something |
| `kioku-lite recall "ENTITY" --hops 2 --limit 15` | Deep dive on one entity |
| `kioku-lite connect "A" "B"` | Connection between two entities |
| `kioku-lite timeline --from DATE --to DATE --limit 20` | Chronological view |
| `kioku-lite entities --limit 50` | See entity vocabulary |
| `kioku-lite kg-alias "CANONICAL" --aliases '["alias1","alias2"]'` | Register aliases |

Mood values: `happy` | `sad` | `excited` | `anxious` | `grateful` | `proud` | `reflective` | `neutral` | `work` | `curious`

---

## Language Handling

- **Respond in the user's language automatically** — detect from their messages.
- **Entity names:** Extract AS-IS in the user's original language — do NOT translate.
- **Entity types & relation types:** Always use English labels (see below).

---

## kg-index — Entity Extraction Rules

You extract entities from text — the engine does NOT do this automatically.

```bash
kioku-lite kg-index <content_hash> \
  --entities '[
    {"name": "Alice", "type": "PERSON"},
    {"name": "Argument with boss", "type": "LIFE_EVENT"},
    {"name": "Stress", "type": "EMOTION"}
  ]' \
  --relationships '[
    {"source": "Stress", "rel_type": "TRIGGERED_BY", "target": "Argument with boss", "evidence": "felt stressed after argument"}
  ]'
```

**Companion persona schema:**
- Entity types: `PERSON` | `EMOTION` | `LIFE_EVENT` | `COPING_MECHANISM` | `PLACE`
- Relation types: `TRIGGERED_BY` | `REDUCED_BY` | `BROUGHT_JOY` | `SHARED_MOMENT_WITH` | `HAPPENED_AT`

**Extraction rules:**
- ✅ Use exact name form: `"Alice"` not `"my friend Alice"`
- ✅ Entity names in the user's original language — do NOT translate
- ❌ Skip generic words: `"I"`, `"we"`, `"they"`, `"team"`
- ❌ Only add relationships explicitly stated in the text
- ✅ No specific entities → skip kg-index

---

## Search Enrichment — Always Enrich Before Searching

Never pass raw user queries to search. Always enrich first:
- Replace pronouns with real names
- Add relevant domain/context keywords
- Use `--entities` for KG-focused boost

---

## Entry Splitting Strategy

**SPLIT into multiple entries if ANY:**
- ≥3 distinct topics | ≥10 entities | ≥2 time phases | >300 words + multiple topics

**Keep as 1 entry if ALL:**
- Single topic, <5 entities, single time point

**How:** Group by phase → topic → emotion. Aim for 5–8 entities per entry. Use relationships to link entries.

---

## Decision Tree

```
Session start?
└─ Check profile → load context with search

User shares new info / "remember this":
└─ Check splitting criteria → save (split if needed) → extract entities → kg-index each

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
