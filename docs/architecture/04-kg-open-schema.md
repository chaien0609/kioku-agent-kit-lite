# KG Open Schema — Extensible Entity & Relationship Types



---

## Summary

The Knowledge Graph in kioku-lite uses an **open schema**: `entity_type` and `rel_type` are plain strings stored directly in SQLite — no fixed enum, no validation. The agent can define any type name on the fly without migrations or code changes.

---

## Why Open Schema?

Personal memory cannot anticipate domains in advance. A user might store:
- **Family** memories (`FAMILY_MEMBER`, `PARENT_OF`)
- **Music** preferences (`MUSIC_ALBUM`, `ARTIST`, `LISTENS_TO`)
- **Books / philosophy** (`BOOK`, `PHILOSOPHY`, `INFLUENCES`)
- **Travel** plans (`TRIP`, `HOTEL`, `DESTINATION`)
- **Skills** being learned (`SKILL`, `COURSE`, `APPLIED_TO`)

A fixed enum would require a new release for each new domain. Open schema lets the agent adapt within a single session.

---

## How It Works

### In the database

Both type columns are plain `TEXT`:

```sql
-- kg_nodes
CREATE TABLE kg_nodes (
    name TEXT PRIMARY KEY,
    type TEXT,          -- "PERSON", "FOOD", "MUSIC_ALBUM", any string
    mention_count INTEGER DEFAULT 0,
    ...
);

-- kg_edges
CREATE TABLE kg_edges (
    source TEXT,
    target TEXT,
    rel_type TEXT,      -- "WORKS_ON", "LISTENS_TO", "PARENT_OF", any string
    ...
);
```

### In code

`upsert_node()` and `upsert_edge()` accept `entity_type: str` and `rel_type: str` directly — no validation:

```python
# graph_store.py
def upsert_node(self, name: str, entity_type: str, date: str) -> None:
    cur.execute(
        "INSERT INTO kg_nodes (name, type, ...) VALUES (?, ?, ...)",
        (name, entity_type, ...),  # stored as-is
    )
```

---

## Convention (not constraint)

`SKILL.md` lists common types to give the agent a baseline, but these are **not enforced**:

**Suggested entity types:**

| Group | Types |
|-------|-------|
| Core | `PERSON`, `ORGANIZATION`, `PLACE`, `EVENT` |
| Work | `PROJECT`, `TOOL`, `CONCEPT` |
| Life | `FOOD`, `BOOK`, `MUSIC_ALBUM`, `FILM` |
| Family | `FAMILY_MEMBER` |
| Learning | `SKILL`, `COURSE`, `AUTHOR` |
| Travel | `TRIP`, `HOTEL`, `MOUNTAIN` |
| Creative | `ARTIST`, `PHILOSOPHER`, `MUSIC_GENRE`, `PHILOSOPHY` |

**Suggested relationship types:**

| Group | Types |
|-------|-------|
| Social | `KNOWS`, `PARENT_OF`, `BONDS_WITH` |
| Work | `WORKS_AT`, `WORKS_ON`, `CONTRIBUTED_TO` |
| Spatial | `LOCATED_AT`, `LOCATED_IN`, `DESTINATION` |
| Creative | `CREATED_BY`, `AUTHORED_BY`, `GENRE` |
| Influence | `INFLUENCES`, `HELPS_WITH`, `APPLIED_TO` |
| Activity | `ENJOYS`, `LISTENS_TO`, `READING`, `LEARNING`, `PLANNING` |
| Structural | `USED_BY`, `BELONGS_TO`, `TAUGHT_BY` |

---

## Verified Test Cases (2026-02-28)

Tested with 6 memory domains, 16 custom entity types, 20+ custom relationship types:

```bash
# 28/28 cases passed
✅ FOOD, RESTAURANT entities → recall, search, connect
✅ MUSIC_ALBUM, ARTIST, MUSIC_GENRE → graph traversal correct
✅ BOOK, PHILOSOPHER, PHILOSOPHY → semantic + entity-boosted search
✅ FAMILY_MEMBER → recall with source_memories hydration
✅ SKILL, COURSE → APPLIED_TO cross-domain connect
✅ TRIP, HOTEL, MOUNTAIN → multi-hop path finding

# Cross-domain connect example
kioku-lite connect "Stoicism" "kioku-lite"
→ {"connected": true, "paths": [["Stoicism", "Alice", "kioku-lite"]]}
# Path: Stoicism INFLUENCES Alice → Alice WORKS_ON kioku-lite ✅
```

---

## When NOT to use custom types

- **Semantic overlap**: No need for both `WORK` and `CAREER` if they mean the same thing — pick one.
- **Too granular**: `PHO_RESTAURANT` instead of `RESTAURANT` makes it harder to search later.
- **Unclear abbreviations**: `ORG` instead of `ORGANIZATION` — use the full name so other agents can read the graph.

**Rule of thumb:** A type should be clear enough that another agent reading the graph immediately understands what kind of entity it is.

---

## Related

- [02-write-save-kg-index.md](02-write-save-kg-index.md) — how kg-index works in the write pipeline
- [SKILL.md](../../src/kioku_lite/resources/SKILL.md) — convention types for agents
