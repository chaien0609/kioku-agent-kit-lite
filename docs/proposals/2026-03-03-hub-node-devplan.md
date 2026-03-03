# Dev Plan: Hub Node Fix — Graph Search Precision

**Created:** 2026-03-03  
**Updated:** 2026-03-03  
**Proposal:** [hub-node-problem.md](./2026-03-03-hub-node-problem.md)

---

## Phase 1 — v0.1.27 (immediate)

> **Goal:** Graph search returns targeted results, not 92% of all memories.
> **Status:** ✅ DONE (v0.1.27) — 173 tests passed

### Task 1A: Exclude self-entity from graph seeds

**File:** `src/kioku_lite/search/graph.py`

```python
# In graph_search(), before seed traversal:
# Find user entity = highest mention_count node
# Skip it as seed — it connects to everything, adds no signal
```

- Detect: `SELECT name FROM kg_nodes ORDER BY mention_count DESC LIMIT 1`
- If entity list contains self-entity → remove it
- If self-entity is the ONLY entity → keep it (fallback)

**Test:** `search "mẹ" --entities "Mẹ,Phúc"` → Phúc removed, only traverse from Mẹ

### Task 1C: Adaptive hop limit by node degree

**File:** `src/kioku_lite/pipeline/graph_store.py`

```python
# In traverse(), before BFS:
degree = edge_count_for(entity_name)
effective_hops = 1 if degree > 15 else min(max_hops, 2)
```

**Test:** Mẹ (10 edges) → 2 hops. Phúc (33 edges) → 1 hop if not already excluded.

### Validation

Replay 4 search queries from acceptance test #2:
- [x] Graph results < 100% coverage — Mẹ query: graph 4→3 ✅
- [x] Relevant memories still retrieved — top results unchanged ✅
- [x] Tests pass (pytest) — 173/173 passed ✅

---

## Phase 2 — ✅ DONE (v0.1.27)

### Task 2H: SKILL.md — guide agent tool selection ✅

Added rules to SKILL.md + companion/mentor TOOLS.md:
- ❌ Do NOT add user's own name to `--entities`
- ❌ Single entity → use `recall` instead
- ✅ Pass 2-3 specific non-user entities

### Task 2E: Multi-entity intersection ✅

**File:** `src/kioku_lite/search/graph.py`

When `len(entities) >= 2`: return memories connected to ALL entities (intersection).  
Fallback to union if intersection is empty.

**Result:** Works correctly. On current DB (36 mem), most multi-entity queries fallback to union because entity memories don't overlap. Will become more effective as KG grows.

---

## Phase 3 — when KG > 500 nodes

| Task | Description |
|---|---|
| 3I | Replace BFS with Personalized PageRank |
| 3G | Community detection (Leiden algorithm) |
| 3J | MMR post-retrieval diversity selection |

*Details in [proposal](./2026-03-03-hub-node-problem.md).*
