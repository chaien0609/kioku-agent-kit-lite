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
kioku-lite search "<UserName> profile background goals recent work challenges" --limit 10
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
    {"name": "Project X", "type": "PROJECT"}
  ]' \
  --relationships '[
    {"source": "Alice", "rel_type": "WORKS_ON", "target": "Project X", "evidence": "working on project X"}
  ]'
```

**Mentor persona schema — use these INSTEAD of generic types:**
- Entity types: `PERSON` | `ORGANIZATION` | `PROJECT` | `EVENT` | `DECISION` | `LESSON_LEARNED` | `STRATEGY` | `CHALLENGE`
- Relation types: `CAUSED_BY` | `RESOLVED_BY` | `RESULTED_IN` | `LED_TO_LESSON` | `APPLIED_STRATEGY` | `WORKS_FOR` | `PARTNERS_WITH`

**Extraction rules:**
- ✅ Use exact name form: `"Alice"` not `"my colleague Alice"`
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

## Decision Tree

```
Session start?
└─ Check profile → load context with search

User shares new info / "remember this":
└─ save → extract entities → kg-index

User asks a question:
└─ ENRICH query → search

User asks about one specific entity / "who is X?":
└─ recall "entity" --hops 2

User asks how X relates to Y:
└─ connect "X" "Y"

"What happened last quarter / last year?":
└─ timeline --from DATE --to DATE

Before giving advice:
└─ ALWAYS search for past lessons first: recall "LESSON_LEARNED" --hops 1
```

Never invent memories. 0 results → be honest with the user.
