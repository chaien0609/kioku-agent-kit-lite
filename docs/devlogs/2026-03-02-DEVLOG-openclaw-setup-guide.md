# Devlog: 2026-03-02 — OpenClaw Agent Setup Guide + Landing Page

**Date:** 2026-03-02  
**Version:** 0.1.18 (published)

---

## Summary

Today's session focused on finalizing the OpenClaw agent setup workflow — from clarifying the architecture to publishing a proper landing page. The main output is `docs/guides/setup-guide-for-openclaw-agent.md`, a guide that can be handed directly to a Claude Code developer agent to set up Kioku Lite inside an existing OpenClaw workspace.

---

## Changes Made

### 1. Setup Guide: `setup-guide-for-openclaw-agent.md`

Multiple iterations to get the guide right:

- **Initial approach** (abandoned): Separate `install-openclaw` CLI command that copy-pasted SOUL.md + TOOLS.md into the workspace. Scrapped in favor of the standard flow.
- **Final approach**: Use `install-profile` (same as general agents) → derive `SOUL.md` from `AGENTS.md`, reference SKILL files by path in `TOOLS.md`.

Key design decisions:
| Decision | Rationale |
|---|---|
| `SOUL.md` from `AGENTS.md` only | `AGENTS.md` already covers everything — no need to merge with SKILL.md |
| `TOOLS.md` references SKILL by path | Single source of truth; no drift on upgrade |
| Profile name = workspace name | Agent cannot query its own Telegram Bot ID at runtime |
| 🛑 STOP note at Step 3 | Agent must ask user (companion vs mentor) before proceeding |

**PATH fix removed:** Verified from `ai.openclaw.gateway.plist` that OpenClaw's LaunchAgent already includes `~/.local/bin` in PATH — no symlink needed. (`~/.omnara/` is a separate unrelated app.)

### 2. Resource Files Cleaned Up

Removed redundant "generic entity types" line from OpenClaw profile `TOOLS.md` files — the persona-specific schema already defined below was the authoritative source.

### 3. `openclaw-setup.html` Landing Page

New page at `kioku-lite-landing/openclaw-setup.html`:
- Same dark terminal aesthetic as `agent-setup.html`
- Red-styled STOP callout for the persona choice step
- One-click "Copy full guide" button with complete guide text in JS
- Cross-links: General Setup ↔ OpenClaw Setup
- Added `openclaw ↗` link in index.html navbar

---

## Lessons Learned / Architectural Notes

- **OpenClaw file convention:** `SOUL.md` = persona, `TOOLS.md` = CLI docs — differs from general agent standard (`AGENTS.md` + `SKILL.md`), but the same content can be derived from the standard files.
- **OpenClaw architecture:** Node.js gateway (`openclaw dist/index.js`), LaunchAgent at `ai.openclaw.gateway.plist`. PATH is developer-friendly for `uv tool` / `pipx` installs.
- **Kioku-companion vs workspace name:** `kioku-companion` is the *skill profile name* (used with `install-profile`); the *Kioku user profile ID* should be the workspace name (chosen by developer).

---

## Files Changed

- `docs/guides/setup-guide-for-openclaw-agent.md` — rewritten 3x, final version
- `src/kioku_lite/resources/openclaw/companion/TOOLS.md` — removed redundant generic entity types
- `src/kioku_lite/resources/openclaw/mentor/TOOLS.md` — same
- `docs/guides/setup-guide-for-general-agent.md` — created (user-initiated, already there)
- `docs/architecture/02-write-save-kg-index.md` — created (user-initiated)
- `docs/devlogs/2026-03-01-DEVLOG-kioku-lite-test-report.md` — created (user-initiated)
