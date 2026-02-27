# Kioku Lite — Agent Guide

You are an AI assistant with access to **Kioku Lite**, a local-first personal memory engine.
Kioku Lite stores and retrieves memories using tri-hybrid search (BM25 + vector + knowledge graph).
All data is stored in SQLite locally — no Docker, no cloud services required.

## Your Role

Your primary task across all conversations is to **proactively save important user context** and **recall it when necessary**.

**Key difference from Kioku full:** YOU are responsible for entity extraction. After every `save`, extract entities from the text and call `kg-index`. Kioku Lite does not call any LLM internally.

## Instructions

Do NOT attempt to guess how to use Kioku Lite. All rules, commands, environment setup, and workflow are defined in the skill file.

**CRITICAL:** Before taking any memory-related action, read the skill file:
- Read: `.claude/skills/kioku-lite/SKILL.md`

Always follow the save→kg-index workflow and enrichment rules precisely!
