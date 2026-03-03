# Devlog: 2026-03-03 — Acceptance Testing & 4 Releases

**Date:** 2026-03-03  
**Versions:** 0.1.23 → 0.1.24 → 0.1.25 → 0.1.26 (all published to PyPI)

---

## Summary

Full day of acceptance testing with the live OpenClaw agent (companion persona) via Telegram. Identified and fixed multiple issues through iterative test → fix → release cycles. Key themes: `event_time` fix, agent memory directive, export-graph bugfix, and tri-hybrid search activation.

---

## Changes Made

### Release 0.1.23 — `event_time` in Search Filters

**Problem:** Temporal queries like "What happened in 2019?" failed because search was filtering on save date (today) instead of event date.

**Fix:**
- `service.py`: prioritize `event_time` over `date` in search result filtering
- `memory_store.py`: add `event_time` to FTS5 SELECT query
- `models.py`: add `event_time` field to `FTSResult`
- `bm25.py`: add `event_time` to `SearchResult`
- `SKILL.md`: mark `--event-time` as **REQUIRED** (not optional)

### Release 0.1.24 — Critical Memory Directive

**Problem:** Agent stored user data in `USER.md` instead of kioku-lite. USER.md is not searchable.

**Fix:** Added 🚨 CRITICAL directive to all template files:
- `SOUL.md` (companion + mentor): "kioku-lite is your ONLY memory system"
- `TOOLS.md` (companion + mentor): "FIRST action is `kioku-lite save`"
- `CLAUDE.agent.md`: same directive for general agents

**Result:** Agent switched from USER.md to kioku-lite save + kg-index immediately.

### Release 0.1.25 — Export Graph Title Fix

**Problem:** "Kioku Knowledge Graph" title displayed twice (pyvis `heading` param renders both h1 + `<title>`).

**Fix:** Set `heading=""` in Network constructor.

### Release 0.1.26 — Tri-Hybrid Search Activation

**Problem:** Graph search backend never triggered because agent didn't pass `--entities`.

**Fix (SKILL.md + all TOOLS.md):**
1. 🚨 "ALWAYS pass `--entities` when query mentions specific entities" — activates graph backend
2. "Prefer proper names over generic labels" — `"Phong"` not `"Con trai"`

**Result:**
| Metric | Before (v0.1.25) | After (v0.1.26) |
|---|---|---|
| `--entities` usage | 0/5 searches | **3/4 searches** |
| Graph contribution | 0% | **62%** |

---

## Testing Results

### Haiku vs Sonnet Comparison

Tested same input ("lưu thông tin + URLs") with both models:

| Metric | Haiku | Sonnet |
|---|---|---|
| Memories | 1 (mega-entry) | **31** (well-split) |
| KG nodes | 27 | **83** |
| event_time accuracy | All wrong (2019) | **9 distinct dates, accurate** |
| Mood diversity | 1 | **7+** |
| Splitting | ❌ | ✅ 14+ entries by timeline |

**Decision:** Switched agent model to `claude-sonnet-4-5`.

### Session Without Chat History

Cleared agent sessions, kept DB. Agent successfully:
- Identified user from DB-only context (no chat history)
- Answered nuanced emotional questions ("tôi có ghét mẹ không?")
- Answered factual questions about people, work, relationships
- Saved new information silently (3 saves + 3 kg-indexes)

### Tri-Hybrid Search Breakdown

Replayed agent's search queries through Python API:

| Query | BM25 | Vector | Graph |
|---|---|---|---|
| Session start (no entities) | 0 | **10** | 0 |
| "mẹ ghét" + entities Mẹ,Phúc | **11** | 0 | **4** |
| "Phong" + entities Phong,Phúc,Con trai | 0 | 0 | **15** |
| "công việc" + entities Phúc,Techbase,Brain,Sato | 0 | 0 | **15** |

Hydration: 100% — all search results return full original text.

---

## Architectural Notes

- **pyvis heading duplication:** `Network(heading=X)` renders X both as visible h1 AND in `<title>`. Use `heading=""` to avoid.
- **Graph backend depends on `--entities`:** Without it, only vector + BM25 are active. This is by design (graph needs seed entities for traversal), but must be documented prominently.
- **Hub node problem:** Entity "Phúc" has high connectivity (14 mentions) → graph queries with Phúc always return everything. May need relevance filtering or hop limits in future.
- **Agent save behavior:** Sonnet saves silently (no "đã lưu" message) — better UX for companion persona.

---

## Files Changed

| File | Change |
|---|---|
| `service.py` | event_time priority in search filter |
| `memory_store.py` | event_time in FTS5 SELECT |
| `models.py` | event_time in FTSResult |
| `bm25.py` | event_time in SearchResult |
| `SKILL.md` | event_time REQUIRED, mandatory --entities, proper name rule |
| `TOOLS.md` (×4) | Memory directive, --entities directive, proper name rule |
| `SOUL.md` (×2) | kioku-lite ONLY memory system |
| `CLAUDE.agent.md` | Same memory directive |
| `export_graph.py` | Fix duplicate heading |
| `architecture/01-system.md` | Version + export-graph in diagram |
| `CHANGELOG.md` | 4 version entries |
| `pyproject.toml` | 0.1.22 → 0.1.26 |

## Test Reports

- `docs/acceptance-test/2026-03-03_2214_tri-hybrid-search-test.md`
- `docs/acceptance-test/2026-03-03_2234_post-fix-search-test.md`
- `docs/acceptance-test/2026-03-03_2216_knowledge-graph.html`
- `docs/acceptance-test/2026-03-03_memory-backup.md`
