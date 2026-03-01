#!/usr/bin/env bash
# Script to auto-generate SKILL.md for a specific use-case template

SET_USE_CASE=$1

if [ -z "$SET_USE_CASE" ]; then
    echo "Usage: ./setup.sh <use_case> (e.g. companion, mentor)"
    exit 1
fi

TEMPLATE_FILE="$(dirname "$0")/../templates/${SET_USE_CASE}.md"
GENERAL_SKILL_FILE="$(dirname "$0")/../SKILL.md"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template '$SET_USE_CASE' not found in resources/templates/"
    exit 1
fi

DEST_DIR="$HOME/.agents/skills/kioku-${SET_USE_CASE}"
mkdir -p "$DEST_DIR"

DEST_FILE="${DEST_DIR}/SKILL.md"

echo "Generating Agent Skill for Kioku Lite: $SET_USE_CASE..."

# 1. Write the YAML frontmatter (extracted from the template)
echo "---" > "$DEST_FILE"
echo "name: kioku-${SET_USE_CASE}" >> "$DEST_FILE"

# Extract description block from template (between ```yaml and ```)
awk '/```yaml/{flag=1; next} /```/{flag=0; next} flag' "$TEMPLATE_FILE" >> "$DEST_FILE"

echo "allowed-tools: Bash(kioku-lite:*)" >> "$DEST_FILE"
echo "---" >> "$DEST_FILE"
echo "" >> "$DEST_FILE"

# 2. Write the main content from the template
cat "$TEMPLATE_FILE" | grep -v '```yaml' | grep -v 'description:' | grep -v '## 1. Description for SKILL.md' | grep -v 'Acts as an emotional companion' | grep -v 'Acts as a strategic business mentor' | grep -v 'Use this skill when' | grep -v 'or reflecting on' | grep -v 'decisions, or reflecting' >> "$DEST_FILE"

echo "" >> "$DEST_FILE"
echo "---" >> "$DEST_FILE"
echo "" >> "$DEST_FILE"
echo "## 5. Standard Kioku Lite CLI Instructions" >> "$DEST_FILE"
echo "> IMPORTANT: The constraints above (Identity & Schema) SUPERSEDE any general examples below." >> "$DEST_FILE"
echo "" >> "$DEST_FILE"

# 3. Append standard CLI usage from the main SKILL.md (skipping the first 15 lines of intro/frontmatter)
tail -n +16 "$GENERAL_SKILL_FILE" >> "$DEST_FILE"

echo "✅ Successfully created Agent Skill at: $DEST_FILE"
echo "Your AI agent will now use this skill when interacting with you."
