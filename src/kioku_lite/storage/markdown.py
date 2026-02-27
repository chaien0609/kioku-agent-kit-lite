"""Markdown-based memory storage — Source of Truth (identical to kioku-agent-kit)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass

JST = timezone(timedelta(hours=7))  # Vietnam timezone


@dataclass
class MemoryEntry:
    text: str
    timestamp: str
    mood: str | None = None
    tags: list[str] | None = None
    event_time: str | None = None


def save_entry(
    memory_dir: Path,
    text: str,
    mood: str | None = None,
    tags: list[str] | None = None,
    event_time: str | None = None,
) -> MemoryEntry:
    """Append a memory entry to today's markdown file."""
    memory_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(JST)
    timestamp = now.isoformat()
    today = now.strftime("%Y-%m-%d")
    filepath = memory_dir / f"{today}.md"

    lines = ["\n---\n", f'time: "{timestamp}"\n']
    if mood:
        lines.append(f'mood: "{mood}"\n')
    if tags:
        lines.append(f"tags: {tags}\n")
    if event_time:
        lines.append(f'event_time: "{event_time}"\n')
    lines.append("---\n")
    lines.append(f"{text}\n")

    if not filepath.exists():
        filepath.write_text(f"# Kioku Lite — {today}\n", encoding="utf-8")

    with filepath.open("a", encoding="utf-8") as f:
        f.writelines(lines)

    return MemoryEntry(text=text, timestamp=timestamp, mood=mood, tags=tags, event_time=event_time)
