# KG Open Schema — Extensible Entity & Relationship Types

> Last updated: 2026-02-28 (v0.1.14)

---

## Tóm tắt

Knowledge Graph trong kioku-lite là **open-schema**: `entity_type` và `rel_type` là plain strings lưu thẳng vào SQLite — không có enum cố định, không có validation. Agent có thể đặt tên type bất kỳ khi nào cần mà không cần migration hay code change.

---

## Tại sao Open Schema?

Personal memory không thể đoán trước được domain. Một người có thể lưu:
- Ký ức về **gia đình** (`FAMILY_MEMBER`, `PARENT_OF`)
- **Âm nhạc** yêu thích (`MUSIC_ALBUM`, `ARTIST`, `LISTENS_TO`)
- **Sách/triết học** đang đọc (`BOOK`, `PHILOSOPHY`, `INFLUENCES`)
- Kế hoạch **du lịch** (`TRIP`, `HOTEL`, `DESTINATION`)
- **Kỹ năng** đang học (`SKILL`, `COURSE`, `APPLIED_TO`)

Nếu dùng enum cố định, mỗi domain mới đều cần release mới. Open schema cho phép agent adapt ngay trong session.

---

## Cơ chế

### Trong database

Hai columns lưu type đều là plain `TEXT`:

```sql
-- kg_nodes
CREATE TABLE kg_nodes (
    name TEXT PRIMARY KEY,
    type TEXT,          -- "PERSON", "FOOD", "MUSIC_ALBUM", bất kỳ string nào
    mention_count INTEGER DEFAULT 0,
    ...
);

-- kg_edges
CREATE TABLE kg_edges (
    source TEXT,
    target TEXT,
    rel_type TEXT,      -- "WORKS_ON", "LISTENS_TO", "PARENT_OF", bất kỳ string nào
    ...
);
```

### Trong code

`upsert_node()` và `upsert_edge()` nhận `entity_type: str` và `rel_type: str` trực tiếp — không qua validation:

```python
# graph_store.py
def upsert_node(self, name: str, entity_type: str, date: str) -> None:
    cur.execute(
        "INSERT INTO kg_nodes (name, type, ...) VALUES (?, ?, ...)",
        (name, entity_type, ...),  # ← stored as-is
    )
```

---

## Convention (không phải constraint)

SKILL.md liệt kê các types phổ biến để agent có baseline, nhưng chúng **không** được enforce:

**Entity types gợi ý:**

| Nhóm | Types |
|------|-------|
| Core | `PERSON`, `ORGANIZATION`, `PLACE`, `EVENT` |
| Work | `PROJECT`, `TOOL`, `CONCEPT` |
| Life | `FOOD`, `BOOK`, `MUSIC_ALBUM`, `FILM` |
| Family | `FAMILY_MEMBER` |
| Learning | `SKILL`, `COURSE`, `AUTHOR` |
| Travel | `TRIP`, `HOTEL`, `MOUNTAIN` |
| Creative | `ARTIST`, `PHILOSOPHER`, `MUSIC_GENRE`, `PHILOSOPHY` |

**Relationship types gợi ý:**

| Nhóm | Types |
|------|-------|
| Social | `KNOWS`, `PARENT_OF`, `BONDS_WITH` |
| Work | `WORKS_AT`, `WORKS_ON`, `CONTRIBUTED_TO` |
| Spatial | `LOCATED_AT`, `LOCATED_IN`, `DESTINATION` |
| Creative | `CREATED_BY`, `AUTHORED_BY`, `GENRE` |
| Influence | `INFLUENCES`, `HELPS_WITH`, `APPLIED_TO` |
| Activity | `ENJOYS`, `LISTENS_TO`, `READING`, `LEARNING`, `PLANNING` |
| Structural | `USED_BY`, `BELONGS_TO`, `TAUGHT_BY` |

---

## Verified Test Cases (2026-02-28)

Test với 6 memory domains, 16 custom entity types mới, 20+ custom relationship types:

```bash
# 28/28 cases passed
✅ FOOD, RESTAURANT entities → recall, search, connect
✅ MUSIC_ALBUM, ARTIST, MUSIC_GENRE → graph traversal đúng
✅ BOOK, PHILOSOPHER, PHILOSOPHY → search semantic + entity-boosted
✅ FAMILY_MEMBER → recall với source_memories hydration
✅ SKILL, COURSE → APPLIED_TO cross-domain connect
✅ TRIP, HOTEL, MOUNTAIN → multi-hop path finding

# Cross-domain connect test
kioku-lite connect "Stoicism" "kioku-lite"
→ {"connected": true, "paths": [["Stoicism", "Phúc", "kioku-lite"]]}
# Path: Stoicism INFLUENCES Phúc → Phúc WORKS_ON kioku-lite ✅
```

Full test script: [`/tmp/test_custom_kg_types.sh`](../devlogs/2026-02-28-TESTLOG-enriched-search.md)

---

## Khi nào không dùng custom types?

- **Trùng lặp ngữ nghĩa**: Không cần cả `WORK` và `CAREER` nếu cùng nghĩa — chọn 1
- **Quá granular**: `PHO_RESTAURANT` thay vì `RESTAURANT` — sẽ khó search sau
- **Abbreviation không rõ**: `ORG` thay vì `ORGANIZATION` — nên dùng tên đầy đủ để agent khác hiểu

**Rule of thumb:** Type nên đủ rõ để một agent khác đọc graph biết ngay đây là entity gì.

---

## Related

- [03-kg-index.md](03-kg-index.md) — cách kg-index hoạt động
- [SKILL.md](../../src/kioku_lite/resources/SKILL.md) — convention types cho agent
