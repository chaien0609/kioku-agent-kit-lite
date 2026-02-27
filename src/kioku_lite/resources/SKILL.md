# Kioku Lite — Agent SKILL

## Overview

Kioku Lite is a **100% local** personal memory engine. Zero Docker, zero cloud LLM.
All commands use the `kioku-lite` CLI. Every bash call requires sourcing the venv:

```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku-lite/config.env | xargs 2>/dev/null) && kioku-lite <command>
```

## Core Commands

### Save a memory
```bash
kioku-lite save "text of the memory" --mood happy --tags work,meeting --event-time 2026-02-20
```
Output includes `content_hash` — use it immediately in `kg-index`.

---

### Index knowledge graph (CRITICAL — run after every save)

After saving, YOU (the agent) must extract entities and relationships from the text,
then index them into the knowledge graph. Kioku Lite does NOT call any LLM internally.

```bash
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"TBV","type":"ORGANIZATION"}]' \
  --relationships '[{"source":"Hùng","target":"TBV","rel_type":"WORKS_AT","weight":0.8,"evidence":"Hùng làm ở TBV"}]'
```

**Entity types**: `PERSON` | `PLACE` | `EVENT` | `EMOTION` | `TOPIC` | `ORGANIZATION` | `PRODUCT`
**Relationship types**: `CAUSAL` | `EMOTIONAL` | `TEMPORAL` | `TOPICAL` | `INVOLVES` | `WORKS_AT` | `KNOWS`
**Rules**:
- Use Vietnamese entity names if text is Vietnamese (e.g. `"mẹ"` not `"mother"`)
- Keep names short and consistent (`"Hùng"` not `"anh Hùng"`)
- `weight`: 0.1 (weak) → 1.0 (strong proven connection)
- `evidence`: exact quote from text supporting the relationship

---

### Register entity aliases (SAME_AS)
```bash
kioku-lite kg-alias "Nguyễn Trọng Phúc" --aliases '["phuc-nt","Phúc","anh","tôi","mình"]'
```

---

### Search memories
```bash
# General search
kioku-lite search "query text" --limit 10

# With entity hints (improves KG leg)
kioku-lite search "Phúc làm gì ở TBV" --entities "Phúc,TBV"

# Temporal filter
kioku-lite search "query" --from 2026-01-01 --to 2026-02-28
```

---

### Recall entity
```bash
kioku-lite recall "Hùng" --hops 2
```

### Explain connection
```bash
kioku-lite connect "Phúc" "LINE Technology"
```

### List entities
```bash
kioku-lite entities --limit 30
```

### Timeline
```bash
kioku-lite timeline --from 2026-02-01 --sort-by event_time
```

---

## Typical Save Workflow (2 steps)

```
Step 1: Save text
  result = kioku-lite save "Hôm nay họp với Hùng và Lan về dự án X. Cả team vui vẻ." --mood happy

Step 2: Index KG (you extract entities from the text above)
  kioku-lite kg-index <content_hash from step 1> \
    --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Lan","type":"PERSON"},{"name":"dự án X","type":"TOPIC"}]' \
    --relationships '[
      {"source":"Hùng","target":"dự án X","rel_type":"INVOLVES","weight":0.7,"evidence":"họp về dự án X"},
      {"source":"Lan","target":"dự án X","rel_type":"INVOLVES","weight":0.7,"evidence":"họp về dự án X"}
    ]'
```

## Data locations

```
~/.kioku-lite/
├── config.env          # configuration
└── users/<user_id>/
    ├── memory/         # Markdown files (source of truth, YYYY-MM-DD.md)
    └── data/
        └── kioku.db    # Single SQLite file: FTS5 + sqlite-vec + KG
```
