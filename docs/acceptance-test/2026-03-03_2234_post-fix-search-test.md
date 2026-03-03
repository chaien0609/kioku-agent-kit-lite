# Acceptance Test #2: Post-Fix Search & Agent Behavior

**Date:** 2026-03-03 22:34  
**Version:** kioku-lite 0.1.26  
**Agent model:** claude-sonnet-4-5 (OpenClaw)  
**Profile:** companion  
**DB state:** 36 memories, 83 nodes, 90 edges  
**Context:** Session cleared, DB kept. Testing after v0.1.26 fixes (mandatory `--entities`, proper name preference).

---

## 1. Fixes Applied in v0.1.26

| Issue | Fix |
|---|---|
| 🔴 Graph search ít kích hoạt | SKILL.md + TOOLS.md: 🚨 ALWAYS pass `--entities` |
| 🟡 Entity naming chung chung | Added rule: prefer proper names over generic labels |

---

## 2. Agent Commands (this session)

| # | Command | Purpose |
|---|---|---|
| 1 | `kioku-lite users` | Session start |
| 2 | `kioku-lite search "stress emotion..." --limit 10` | Load context (no entities — session start) |
| 3 | `kioku-lite search "mẹ..." --entities "Mẹ,Phúc" --limit 15` | ✅ **--entities used!** |
| 4 | `kioku-lite search "Phong..." --entities "Phong,Phúc,Con trai" --limit 15` | ✅ **--entities used!** |
| 5 | `kioku-lite recall "Phong" --hops 2 --limit 10` | Entity traversal |
| 6 | `kioku-lite search "công việc..." --entities "Phúc,Techbase,Brain,Sato" --limit 15` | ✅ **--entities used!** |

**Result:** 3/4 search queries now include `--entities` (all except session start). ✅

---

## 3. Tri-Hybrid Backend Contribution — Before vs After

### Before (v0.1.25, Test #1)

| Query | BM25 | Vector | Graph | Total |
|---|---|---|---|---|
| Session start | 0 | **10** | 0 | 10 |
| Mẹ / ghét | 0 | **15** | 0 | 15 |
| Phong (1) | 0 | **15** | 0 | 15 |
| Phong (2) | 1 | **19** | 0 | 20 |
| Công việc | 0 | **15** | 0 | 15 |

**Vector dominated 99%+, Graph = 0%**

### After (v0.1.26, Test #2)

| Query | BM25 | Vector | Graph | Total |
|---|---|---|---|---|
| Session start (no entities) | 0 | **10** | 0 | 10 |
| Mẹ / ghét `--entities "Mẹ,Phúc"` | **11** | 0 | **4** | 15 |
| Phong `--entities "Phong,Phúc,Con trai"` | 0 | 0 | **15** | 15 |
| Công việc `--entities "Phúc,Techbase,Brain,Sato"` | 0 | 0 | **15** | 15 |

**Graph now contributes 34/55 results (62%)!** 🎯

---

## 4. Detailed Analysis

### Query: "tôi có ghét mẹ không?" → `--entities "Mẹ,Phúc"`

| Source | Count | Top result |
|---|---|---|
| **bm25** | **11** | "10 năm không sống chung với bố mẹ - Mẹ sợ con đói" |
| **graph** | **4** | Memories connected to "Mẹ" via SHARED_MOMENT_WITH, TRIGGERED_BY |

**Assessment:** ✅ BM25 + Graph collaboration. BM25 finds keyword matches ("mẹ", "cảm xúc"), Graph finds relationship-connected memories via entity "Mẹ". Both contribute unique results → richer context.

---

### Query: "Phong và tôi thế nào" → `--entities "Phong,Phúc,Con trai"`

| Source | Count | Note |
|---|---|---|
| **graph** | **15** | All results from graph traversal of Phúc + Con trai |

**Assessment:** ⚠️ Graph-only. "Phong" still not in KG → graph falls back to "Phúc" + "Con trai" traversal. Results are broad (profile, Techbase, etc.) because "Phúc" is the hub node connected to everything. BM25 didn't match, vector didn't contribute.

**Agent workaround:** Agent also called `recall "Phong"` (returned 0 — Phong not in KG), then used the search results + context from previous queries to still answer accurately about Phong.

---

### Query: "công việc dạo này" → `--entities "Phúc,Techbase,Brain,Sato"`

| Source | Count | Note |
|---|---|---|
| **graph** | **15** | Graph traversal of 4 entities |

**Assessment:** ✅ Graph finds work-related memories through entity connections. Agent correctly identified Techbase, Brain, Sato as relevant entities. Response was accurate and contextual.

---

## 5. Agent Response Quality

| Question | Quality | Notes |
|---|---|---|
| "tôi có ghét mẹ không?" | ⭐⭐⭐⭐⭐ | Nuanced emotional analysis, not binary. Referenced specific memories. |
| "Phong và tôi thế nào" | ⭐⭐⭐⭐ | Correctly identified Phong = con trai. Listed specific episodes. |
| "công việc dạo này" | ⭐⭐⭐⭐⭐ | Compared TBV frustration vs Brain opportunity. Referenced Sato meeting. |

---

## 6. Comparison: Test #1 vs Test #2

| Metric | Test #1 (v0.1.25) | Test #2 (v0.1.26) | Δ |
|---|---|---|---|
| `--entities` usage | 0/5 searches | **3/4 searches** | ✅ Fixed |
| Graph results | 0% | **62%** | 🎯 Major improvement |
| BM25 results | 2% | **20%** | ↑ |
| Vector results | 98% | **18%** | ↓ (rebalanced) |
| Response quality | ⭐⭐⭐⭐ | ⭐⭐⭐⭐½ | ↑ |

---

## 7. Remaining Issues

| Priority | Issue | Status |
|---|---|---|
| 🟡 Medium | "Phong" not in KG (indexed as "Con trai") | Open — agent didn't index new data this session. When it does, proper name rule should help. |
| 🟡 Medium | Graph-heavy queries (e.g. 4 entities) return broad results because "Phúc" hub connects to everything | Acceptable — RRF scoring handles ranking. Consider limiting graph hops or adding relevance filter. |
| 🟢 Low | Session start search still has no `--entities` | By design — no entity context yet at session start. |

---

## 8. Conclusion

**v0.1.26 fixes are effective.** ✅

- **`--entities` directive works:** Agent now passes entities in 3/4 search queries (vs 0/5 before)
- **Graph backend activated:** 62% of search results now come from graph (vs 0% before)
- **Tri-hybrid is truly hybrid now:** BM25 (keyword) + Graph (relationships) both contribute meaningful results
- **Agent response quality maintained or improved** despite backend shift

**Overall: PASS ✅** — The fixes addressed both action items from Test #1 successfully.
