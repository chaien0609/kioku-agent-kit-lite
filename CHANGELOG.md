# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.23] — 2026-03-03

### Fixed
- **Search date filter now uses `event_time`** when available, falling back to `date`. Previously all temporal queries ("năm 2019") returned 0 results because memories were filtered by processing date (today) instead of event date.

### Changed
- `FTSResult` and `SearchResult` now carry `event_time` field through the search pipeline
- Search output includes `event_time` in results JSON
- SKILL.md: `--event-time` is now marked as REQUIRED on `save` (not just `kg-index`)

## [0.1.22] — 2026-03-03

### Changed
- **Restructured SKILL.md** — clearer sections, less redundancy, same 11 sections but more substance
- **kg-index now a 3-step process**: disambiguate (check existing entities) → extract → index
- Added `--event-time` documentation to kg-index with relative date parsing guide
- Added entity disambiguation guidance: check `kioku-lite entities` before extracting
- Clarified `evidence` field: must be exact quote from saved text
- Updated OpenClaw TOOLS.md templates (companion + mentor) with same improvements

## [0.1.21] — 2026-03-03

### Added
- **Entry Splitting Strategy** in SKILL.md — quantifiable criteria for when agents should split large saves into multiple focused entries (≥3 topics, ≥10 entities, ≥2 time phases, >300 words + multiple topics)
- Entry splitting rules added to OpenClaw TOOLS.md templates (companion + mentor profiles)

### Changed
- Decision tree updated: save step now includes splitting check before kg-index

## [0.1.18] — 2026-03-02

### Added
- Setup guide for OpenClaw agent integration (`docs/guides/setup-guide-for-openclaw-agent.md`)
- Telegram-specific setup guide (`docs/guides/openclaw-telegram-setup.md`)
- Architecture documentation: system overview, write pipeline, search pipeline, KG open schema

### Changed
- Removed PATH symlink requirement for OpenClaw — `~/.local/bin` is already in OpenClaw's LaunchAgent PATH
- Cleaned up redundant generic entity types from OpenClaw profile TOOLS.md files

## [0.1.15] — 2026-03-01

### Added
- Agent Profile System: built-in personas via `kioku-lite install-profile <name>`
  - `companion` — emotional companion with schema: EMOTION, LIFE_EVENT, TRIGGERED_BY
  - `mentor` — business & career mentor with schema: DECISION, LESSON_LEARNED, LED_TO_LESSON
- Profile files: each persona includes pre-written `AGENTS.md` + `SKILL.md`, deployable instantly

### Fixed
- `kioku-lite init` now creates `AGENTS.md` instead of `CLAUDE.md` (open standard compatible)
- Skill directory changed from `.claude/skills/` to `.agents/skills/` (works with Claude Code, Cursor, Windsurf)

## [0.1.14] — 2026-02-28

### Fixed
- **`connect` always returned empty `source_memories`** (two-part bug):
  - `find_path()` in `graph_store.py` did not fetch `source_hash` from DB
  - `explain_connection()` in `service.py` used `.values()` instead of `.items()`, losing hash keys
- `source_memories` now includes `content`, `date`, `mood`, and `content_hash`

## [0.1.13] — 2026-02-28

### Fixed
- SKILL.md: `explain-connection` → `connect` (3 occurrences corrected to match actual CLI command)

## [0.1.12] — 2026-02-28

### Added
- Enriched search workflow in SKILL.md (Section 6): 5-step decision tree with 6 query case types
- Agent query enrichment: pronoun resolution, implicit entities, type inference, temporal ranges

## [0.1.11] — 2026-02-28

### Fixed
- **BM25 search always returned 0 results**: FTS5 was doing phrase match instead of term match
- **`content_hash` missing from search/recall/timeline output**: agent could not reference memories for `kg-index`
- FastEmbed pooling-method warning suppressed (cosmetic, not functional)

## [0.1.0] — 2026-02-27

### Added
- Initial release of kioku-lite
- Tri-hybrid search: BM25 (SQLite FTS5) + Vector (sqlite-vec) + Knowledge Graph
- FastEmbed ONNX embedder — local, offline-capable (`intfloat/multilingual-e5-large`)
- OllamaEmbedder — HTTP-based for dev/benchmark comparison
- CLI commands: `save`, `search`, `kg-index`, `recall`, `connect`, `entities`, `timeline`, `users`
- Agent-driven KG indexing via `kg-index` command
- Multi-user support via `kioku-lite users` with profile isolation
- SQLite-based graph store (BFS traversal, entity aliases, open schema)
- Markdown file storage (human-readable backup, source of truth)
- Comprehensive test suite: 149+ tests across 5 modules
- PyPI-ready packaging via Hatchling

### Architecture Decisions
- Zero Docker — all storage in a single SQLite file
- Agent-driven KG: kioku-lite stores what the agent provides; no built-in LLM calls
- Embedding default: `intfloat/multilingual-e5-large` (1024-dim, multilingual, 100+ languages)
- E5 instruction format: `passage:` for indexing, `query:` for search
- Open KG schema: entity types and relationship types are plain strings, not fixed enums

### Benchmark (vs kioku-agent-kit full Docker)
- Search latency: **1.2s vs 2–3s** (kioku-lite 1.7–7.6× faster)
- Precision@3: **0.60 = 0.60** (equal quality with same KG extraction)
- Infrastructure: `pip install` vs 3 Docker containers
