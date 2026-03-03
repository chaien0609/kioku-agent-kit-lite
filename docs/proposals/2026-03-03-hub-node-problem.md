# Proposal: Hub Node Problem — Graph Search Returns Too Broad Results

**Date:** 2026-03-03  
**Status:** Proposal  
**Related:** Acceptance Test → Action Items → "Phúc" hub node

---

## Problem Statement

Entity "Phúc" has **33 edges** (33 mentions) — the highest in KG.  
BFS traversal with `max_hops=2` reaches **92% of all memories** (33/36).

When agent searches with `--entities "Phúc,..."`, graph backend returns nearly everything → dilutes signal.

```
"Phúc" 1-hop → 23 memories (64%)
"Phúc" 2-hop → 33 memories (92%)
Total memories: 36
```

This is the **"supernode" problem** — common in knowledge graphs where one entity is the subject of the entire database.

---

## Root Cause Analysis

The core issue is that in personal memory KGs, **the user themselves is always the hub**. Every memory involves them. This is fundamentally different from generic KGs where no single entity dominates.

Contributing factors:
1. `max_hops=2` is too generous for a hub node with 33 direct connections
2. No query-awareness in graph traversal — BFS doesn't know what the search is about
3. All edges have equal weight (0.5 default) — no way to prioritize relevant ones
4. `graph_search()` ranks seeds by `mention_count` → Phúc always comes first

---

## Proposed Solutions (Ranked by Impact/Effort)

### Solution A: Exclude "self" entity from graph seeds ⭐ RECOMMENDED

**Idea:** The user's own entity (e.g. "Phúc") is always present → it adds no signal. Skip it as a seed, use only other entities.

**Implementation:**
```python
# graph_search() in search/graph.py
def graph_search(store, query, limit=20, entities=None):
    # Skip the user entity — it connects to everything
    user_entity = _get_user_entity(store)  # entity with highest mention_count
    if entities and user_entity:
        entities = [e for e in entities if e.lower() != user_entity.lower()]
```

**Pros:** Simple, effective. The other entities (Mẹ, Techbase, Sato) are the actual signal.  
**Cons:** Edge case if user is the ONLY entity in the query.  
**Effort:** ~10 lines of code. Low risk.

---

### Solution B: Query-aware edge scoring

**Idea:** Score graph edges by text similarity to the original query, not just graph weight.

**Implementation:**
```python
# In graph_search(), after collecting edges:
for edge in traversal.edges:
    # Boost score if evidence text is semantically relevant to the query
    text_overlap = _jaccard_similarity(query_tokens, edge.evidence_tokens)
    edge.score = edge.weight * (1 + text_overlap * 2)
```

**Pros:** Returns only graph results relevant to query topic.  
**Cons:** More computation. May hurt recall for associative queries.  
**Effort:** Medium (~30 lines).

---

### Solution C: Adaptive hop limit based on node degree

**Idea:** Hub nodes get fewer hops. Low-connectivity nodes get more.

**Implementation:**
```python
# In graph_store.py traverse():
degree = self._get_degree(entity_name)
if degree > 15:
    effective_hops = 1  # Hub → 1 hop only
elif degree > 5:
    effective_hops = min(max_hops, 2)
else:
    effective_hops = max_hops  # Leaf → full traversal
```

**Pros:** Natural scaling. Hubs automatically constrained.  
**Cons:** May miss important 2-hop connections from hubs.  
**Effort:** Low (~15 lines).

---

### Solution D: RRF weight adjustment per source

**Idea:** Give less weight to graph results when graph returns many items (likely noisy).

**Implementation:**
```python
# In reranker.py rrf_rerank():
source_weights = {
    'bm25': 1.0,
    'vector': 1.0,
    'graph': 1.0 / max(1, len(graph_results) / limit)  # Penalize flood
}
rrf_score = source_weights[result.source] / (k + rank_pos + 1)
```

**Pros:** Self-regulating. Graph noise automatically down-weighted.  
**Cons:** May under-weight good graph results in legitimate broad queries.  
**Effort:** Low (~10 lines).

---

### Solution E: Multi-entity intersection (instead of union)

**Idea:** When multiple entities are passed, only return memories connected to **all** of them (intersection), not any of them (union).

**Current:** `--entities "Phúc,Mẹ"` → BFS from Phúc (33 results) ∪ BFS from Mẹ (10 results) = broad  
**Proposed:** → BFS from Phúc ∩ BFS from Mẹ = only memories about Phúc AND Mẹ together

**Implementation:**
```python
# In graph_search():
per_entity_hashes = []
for entity in ranked_seeds:
    traversal = store.traverse(entity.name, max_hops=2, limit=limit)
    hashes = {e.source_hash for e in traversal.edges if e.source_hash}
    per_entity_hashes.append(hashes)

if len(per_entity_hashes) > 1:
    common = set.intersection(*per_entity_hashes)
    results = [r for r in results if r.content_hash in common]
```

**Pros:** Precisely targeted results.  
**Cons:** May return 0 results if entities never co-occur in same memory.  
**Effort:** Medium (~20 lines). Needs fallback to union.

## Industry Research — Established Approaches

### F: Neo4j Supernode Strategies (neo4j.com, Medium)

Neo4j documents the supernode problem extensively. Their recommended strategies:

1. **Label segregation** — tag hub nodes with a special label, then exclude them from certain traversals. Analogous to our Solution A.
2. **Directed relationship filtering** — only follow edges in one direction. In our case: follow `source→target` only from seed, not `target→source` (which pulls in everything connected TO the hub).
3. **Degree-based cutoff (`degreeCutoff`)** — Neo4j GDS library offers `upperDegreeCutoff` to exclude nodes above a degree threshold from algorithm participation. Directly maps to Solution C.
4. **Refactoring (cloning)** — split a supernode into sub-clusters with `SAME_AS` links. Last resort, high complexity. Not appropriate for our scale.

**Applicable:** Label segregation (A) + degree cutoff (C) are validated by Neo4j as best practices.

---

### G: Microsoft GraphRAG — Community Detection (microsoft.com, arxiv.org)

Microsoft's GraphRAG framework solves the "global query" problem using **hierarchical community detection** (Leiden algorithm):

1. Cluster related entities into communities
2. Generate LLM summaries per community
3. Query at community level, not entity level

For our case, this means:
- Instead of traversing from "Phúc", identify communities like `{Phúc, Mẹ, Bố, gia đình}`, `{Phúc, Techbase, Brain, career}`, `{Phúc, đọc sách, viết, hobby}`
- Graph search returns memories from the **most relevant community**, not from the entire hub neighborhood

**Applicable:** Future — requires community detection + summarization. Overkill now, but strong long-term foundation as KG grows (100+ nodes).

---

### H: LightRAG Dual-Level Retrieval (arxiv.org, dev.to)

LightRAG (a lightweight GraphRAG alternative) uses **dual-level retrieval**:
- **Low-level**: Specific entity search (like our `recall`)
- **High-level**: Broader concept/theme search

Key insight: **incrementally updateable** without full rebuild, and only costs ~$0.15 vs GraphRAG's ~$4.

For our case:
- Low-level = `recall "Mẹ"` (entity-specific, focused)
- High-level = `search "relationship with mother"` (semantic, broader)
- The agent should choose the right level based on query intent

**Applicable:** Our current architecture already supports this pattern via `recall` vs `search`. The fix is teaching the SKILL.md to guide agent toward `recall` for entity-focused queries instead of always using `search --entities`.

---

### I: Personalized PageRank (Neo4j, Twitter)

Instead of BFS traversal, use **Personalized PageRank (PPR)** from the seed entity:
- Random walk with restart bias toward seed node
- Naturally decays importance with distance
- Used in Twitter's "Who to Follow" recommendation

**Implementation sketch:**
```python
def personalized_pagerank(store, seed, alpha=0.15, max_iter=50):
    # Initialize: all probability mass on seed
    scores = {seed: 1.0}
    for _ in range(max_iter):
        new_scores = {}
        for node, score in scores.items():
            neighbors = store.get_neighbors(node)
            for n in neighbors:
                new_scores[n] = new_scores.get(n, 0) + score / len(neighbors) * (1 - alpha)
            new_scores[seed] = new_scores.get(seed, 0) + score * alpha  # restart bias
        scores = new_scores
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Pros:** Mathematically principled. Handles hubs naturally (mass disperses evenly across many neighbors → low per-neighbor score). No need for arbitrary degree cutoffs.
**Cons:** More computation than BFS. May not be worth it for <100 node graphs.
**Applicable:** Medium-term — elegant solution when graph grows beyond 200+ nodes.

---

### J: MMR (Maximum Marginal Relevance) Selection (Graph RAG literature)

After graph traversal, apply **MMR** to select diverse, non-redundant results:

```python
def mmr_select(results, query_embedding, lambda_=0.7, limit=10):
    selected = []
    while len(selected) < limit and results:
        best = max(results, key=lambda r: 
            lambda_ * similarity(r, query_embedding) - 
            (1 - lambda_) * max(similarity(r, s) for s in selected) if selected else 0
        )
        selected.append(best)
        results.remove(best)
    return selected
```

**Pros:** Balances relevance + diversity. Prevents 15 results all from same neighborhood.  
**Cons:** Requires embeddings for results. Adds latency.  
**Applicable:** Medium-term — useful when graph produces 30+ candidate results.

---

## Updated Recommendation

### Short-term (v0.1.27) — 2 changes, low risk

| Solution | Source | Effort |
|---|---|---|
| **A: Exclude self-entity** | Neo4j label segregation | ~10 lines |
| **C: Adaptive hop limit** | Neo4j degree cutoff | ~15 lines |

These are validated by Neo4j as industry standard. Combined, they solve 90% of the problem.

### Medium-term — when KG reaches 100+ nodes

| Solution | Source | Effort |
|---|---|---|
| **E: Multi-entity intersection** | Original proposal | ~20 lines |
| **H: Dual-level retrieval guidance** | LightRAG | SKILL.md only |

### Long-term — when KG reaches 500+ nodes

| Solution | Source | Effort |
|---|---|---|
| **I: Personalized PageRank** | Neo4j/Twitter | Replace BFS |
| **G: Community detection** | Microsoft GraphRAG / Leiden | Major refactor |
| **J: MMR diversity selection** | Graph RAG literature | Post-retrieval step |

---

## Validation Plan

After implementing A + C:
1. Replay the same 4 search queries from Test #2
2. Verify graph results are more targeted (not 15/15 = graph)
3. Check that relevant memories are still retrieved
4. Measure: % of graph results directly mentioning queried entities in evidence text

---

## References

- Neo4j: [Dealing with Dense Nodes / Supernodes](https://medium.com/neo4j) — label segregation, degree cutoff, refactoring
- Microsoft: [GraphRAG: From Local to Global](https://microsoft.github.io/graphrag/) — Leiden community detection, hierarchical summaries
- LightRAG: [arxiv.org](https://arxiv.org) — dual-level retrieval, incremental updates
- Neo4j GDS: [Personalized PageRank](https://neo4j.com/docs/graph-data-science/) — random walk with restart
- Graph RAG filtering: [arxiv.org](https://arxiv.org) — MMR, subgraph scoring, two-stage filtering

