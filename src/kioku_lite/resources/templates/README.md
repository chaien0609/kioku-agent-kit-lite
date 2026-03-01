# Kioku Lite Templates: Use-Case Driven Knowledge Graphs

> **For AI Agents:** This folder contains reference templates for adapting Kioku Lite to different user needs. When the user wants to set up Kioku Lite for a specific purpose (e.g., as a diary, a business mentor, etc.), read the corresponding file in this folder (`companion.md`, `mentor.md`) to understand the recommended Agent Identity and Knowledge Graph (KG) Schema. 
> You can then generate the appropriate configuration files (like Agent Skills `SKILL.md` or OpenClaw prompts) for the user.

## The Concept of Open-Schema

Kioku Lite uses an **open-schema Knowledge Graph**. This means `entity_type` and `rel_type` can be any string. To maximize search effectiveness, you should stick to a consistent set of types tailored to the user's specific use case.

When configuring a workspace for a user, define the following based on the chosen template:
1. **Agent Identity:** How you should act (Tone, Personality, Directives).
2. **Entity Types:** What concepts matter most in this domain.
3. **Relationship Types:** How those concepts connect (Crucial for multi-hop reasoning).

## Instructions for Agents Configuration

**If the user uses the `AGENTS.md` & Agent Skills standard:**
Create a skill file at `.agents/skills/kioku-<use-case>/SKILL.md` combining the general `kioku-lite` CLI instructions (from `../SKILL.md`) with the specific Identity and KG Schema from the chosen template.

**Example structure for `.agents/skills/kioku-[use-case]/SKILL.md`:**
```markdown
---
name: kioku-[use-case]
description: [Insert description from template]
allowed-tools: Bash(kioku-lite:*)
---
# Kioku [Use Case Name]

## 1. Role & Identity
[Insert Identity Directives]

## 2. KG Schema Constraints
[Insert Entity Types]
[Insert Relationship Types]

## 3. Workflow & Usage
[Insert details from the template's workflow section]
[Insert standard kioku-lite CLI instructions for save, kg-index, search, recall, etc.]
```

**Custom Use Cases:** If the user requests a new use case not covered by the existing templates (e.g., "Fitness Tracker", "Research Assistant"), invent a new set of Entity and Relationship types that fit the domain, and document them in the skill file following the same pattern as the templates.
