"""Kioku Lite CLI — zero Docker, zero cloud LLM.

Commands:
  save        Save a memory. Returns content_hash for kg-index.
  search      Tri-hybrid search (BM25 + Vector + Graph).
  kg-index    Agent-provided entity/relationship indexing for a saved memory.
  kg-alias    Register SAME_AS aliases for a canonical entity.
  recall      Recall everything related to an entity.
  connect     Explain connection between two entities.
  entities    List top entities in the knowledge graph.
  timeline    Chronological memory list.
  setup       First-time setup (download embedding model, create config).
  init        Generate CLAUDE.md + SKILL.md for Claude Code / Cursor.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    raise ImportError("Install with: pip install kioku-agent-kit-lite[cli]")

app = typer.Typer(
    name="kioku-lite",
    help="Personal memory agent — zero Docker, zero cloud LLM.",
    no_args_is_help=True,
)

_svc = None


def _get_svc():
    global _svc
    if _svc is None:
        from kioku_lite.service import KiokuLiteService
        _svc = KiokuLiteService()
    return _svc


def _out(data: dict | str) -> None:
    if isinstance(data, str):
        typer.echo(data)
    else:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


# ── save ───────────────────────────────────────────────────────────────────────

@app.command()
def save(
    text: str = typer.Argument(..., help="Memory text to save."),
    mood: Optional[str] = typer.Option(None, "--mood", "-m"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags."),
    event_time: Optional[str] = typer.Option(None, "--event-time", "-e", help="When it happened (YYYY-MM-DD)."),
) -> None:
    """Save a memory. Prints content_hash — use it with kg-index to add KG entries."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    result = _get_svc().save_memory(text, mood=mood, tags=tag_list, event_time=event_time)
    _out(result)


# ── kg-index ───────────────────────────────────────────────────────────────────

@app.command(name="kg-index")
def kg_index(
    content_hash: str = typer.Argument(..., help="content_hash returned by `save`."),
    entities: Optional[str] = typer.Option(
        None, "--entities", "-e",
        help='JSON array of entities. Example: \'[{"name":"Phúc","type":"PERSON"}]\''
    ),
    relationships: Optional[str] = typer.Option(
        None, "--relationships", "-r",
        help='JSON array of relationships. Example: \'[{"source":"Phúc","target":"TBV","rel_type":"WORKS_AT","weight":0.8,"evidence":"..."}]\''
    ),
    event_time: Optional[str] = typer.Option(None, "--event-time", help="YYYY-MM-DD when the event happened."),
) -> None:
    """Index agent-extracted entities and relationships for a saved memory.

    The agent (Claude Code / OpenClaw) calls this AFTER `save`, providing
    entities and relationships it already extracted from conversation context.
    Kioku Lite does NOT call any LLM — it simply stores what the agent provides.

    Example workflow (agent SKILL.md):

      1. hash = `kioku-lite save "Hôm nay gặp Hùng ở TBV..." --mood happy`
      2. Agent extracts: entities=[Hùng/PERSON, TBV/PLACE], rel=[Hùng→TBV WORKS_AT]
      3. `kioku-lite kg-index <hash> --entities '[...]' --relationships '[...]'`
    """
    from kioku_lite.service import EntityInput, RelationshipInput

    entity_list: list[EntityInput] = []
    if entities:
        try:
            raw = json.loads(entities)
            entity_list = [EntityInput(name=e["name"], type=e.get("type", "TOPIC")) for e in raw]
        except (json.JSONDecodeError, KeyError) as err:
            typer.echo(f"Error parsing --entities JSON: {err}", err=True)
            raise typer.Exit(1)

    rel_list: list[RelationshipInput] = []
    if relationships:
        try:
            raw = json.loads(relationships)
            rel_list = [
                RelationshipInput(
                    source=r["source"], target=r["target"],
                    rel_type=r.get("rel_type", "TOPICAL"),
                    weight=r.get("weight", 0.5),
                    evidence=r.get("evidence", ""),
                )
                for r in raw
            ]
        except (json.JSONDecodeError, KeyError) as err:
            typer.echo(f"Error parsing --relationships JSON: {err}", err=True)
            raise typer.Exit(1)

    result = _get_svc().kg_index(content_hash, entity_list, rel_list, event_time=event_time)
    _out(result)


# ── kg-alias ───────────────────────────────────────────────────────────────────

@app.command(name="kg-alias")
def kg_alias(
    canonical: str = typer.Argument(..., help="The canonical entity name."),
    aliases: str = typer.Option(
        ..., "--aliases", "-a",
        help='JSON array of alias names. Example: \'["phuc-nt","anh","Phúc"]\''
    ),
) -> None:
    """Register SAME_AS aliases for a canonical entity.

    Example:
      kioku-lite kg-alias "Nguyễn Trọng Phúc" --aliases '["phuc-nt","Phúc","anh","tôi"]'
    """
    try:
        alias_list = json.loads(aliases)
    except json.JSONDecodeError as err:
        typer.echo(f"Error parsing --aliases JSON: {err}", err=True)
        raise typer.Exit(1)
    _out(_get_svc().kg_alias(canonical, alias_list))


# ── search ─────────────────────────────────────────────────────────────────────

@app.command()
def search(
    query: str = typer.Argument(..., help="What to search for."),
    limit: int = typer.Option(10, "--limit", "-l"),
    date_from: Optional[str] = typer.Option(None, "--from", help="Start date YYYY-MM-DD."),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date YYYY-MM-DD."),
    entities: Optional[str] = typer.Option(None, "--entities", "-e", help="Comma-separated entity names for KG seeding."),
) -> None:
    """Tri-hybrid search: BM25 + Vector (FastEmbed) + Knowledge Graph → RRF rerank."""
    entity_list = [e.strip() for e in entities.split(",")] if entities else None
    _out(_get_svc().search_memories(query, limit=limit, date_from=date_from, date_to=date_to, entities=entity_list))


# ── recall ─────────────────────────────────────────────────────────────────────

@app.command()
def recall(
    entity: str = typer.Argument(..., help="Entity name to recall memories for."),
    hops: int = typer.Option(2, "--hops", help="Graph traversal depth."),
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    """Recall all memories related to an entity via knowledge graph traversal."""
    _out(_get_svc().recall_entity(entity, max_hops=hops, limit=limit))


# ── connect ────────────────────────────────────────────────────────────────────

@app.command()
def connect(
    entity_a: str = typer.Argument(...),
    entity_b: str = typer.Argument(...),
) -> None:
    """Explain how two entities are connected in the knowledge graph."""
    _out(_get_svc().explain_connection(entity_a, entity_b))


# ── entities ───────────────────────────────────────────────────────────────────

@app.command()
def entities(
    limit: int = typer.Option(50, "--limit", "-l"),
) -> None:
    """List top canonical entities from the knowledge graph."""
    _out(_get_svc().list_entities(limit=limit))


# ── timeline ───────────────────────────────────────────────────────────────────

@app.command()
def timeline(
    start_date: Optional[str] = typer.Option(None, "--from"),
    end_date: Optional[str] = typer.Option(None, "--to"),
    limit: int = typer.Option(50, "--limit", "-l"),
    sort_by: str = typer.Option("processing_time", "--sort-by", "-s", help="'processing_time' or 'event_time'."),
) -> None:
    """Chronological memory list."""
    _out(_get_svc().get_timeline(start_date=start_date, end_date=end_date, limit=limit, sort_by=sort_by))


# ── setup ──────────────────────────────────────────────────────────────────────

@app.command()
def setup(
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="Your user ID (default: personal)."),
) -> None:
    """First-time setup: create config and download embedding model (no Docker needed).

    The FastEmbed model (bge-m3, ~1GB) is downloaded once to ~/.cache/fastembed/
    and reused on all subsequent runs.
    """
    resolved_user_id = user_id or os.environ.get("KIOKU_LITE_USER_ID", "personal")

    typer.echo("")
    typer.echo("╔══════════════════════════════════════╗")
    typer.echo("║   Kioku Agent Kit Lite — Setup       ║")
    typer.echo("║   Zero Docker · Zero Cloud LLM       ║")
    typer.echo("╚══════════════════════════════════════╝")
    typer.echo("")
    typer.echo(f"User ID : {resolved_user_id}")

    # Config file
    config_dir = Path.home() / ".kioku-lite"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.env"

    if config_file.exists():
        typer.echo(f"  ✅ Config already exists: {config_file}")
    else:
        from datetime import date
        config_file.write_text(
            f"""# Kioku Agent Kit Lite — Configuration
# Generated: {date.today()}

KIOKU_LITE_USER_ID={resolved_user_id}

# Embedding model (FastEmbed ONNX — downloaded on first use, ~1GB)
KIOKU_LITE_EMBED_MODEL=BAAI/bge-m3
KIOKU_LITE_EMBED_DIM=1024

# Set to "fake" to skip model download (BM25 + Graph still work):
# KIOKU_LITE_EMBED_PROVIDER=fake
""",
            encoding="utf-8",
        )
        typer.echo(f"  ✅ Created: {config_file}")

    # Warm up embedding model (triggers download if first run)
    typer.echo("")
    typer.echo("── Embedding model (FastEmbed bge-m3) ──")
    typer.echo("   Downloading on first run (~1GB to ~/.cache/fastembed/)...")
    try:
        from kioku_lite.pipeline.embedder import FastEmbedder
        embedder = FastEmbedder(model_name="BAAI/bge-m3")
        embedder.embed("test")
        typer.echo("  ✅ Embedding model ready")
    except Exception as e:
        typer.echo(f"  ⚠️  Model download failed: {e}")
        typer.echo("      Run `kioku-lite setup` again when online,")
        typer.echo("      or set KIOKU_LITE_EMBED_PROVIDER=fake to use BM25+Graph only.")

    typer.echo("")
    typer.echo("╔══════════════════════════════════════╗")
    typer.echo("║         Setup Complete! 🎉           ║")
    typer.echo("╚══════════════════════════════════════╝")
    typer.echo("")
    typer.echo("Quick start:")
    typer.echo(f"  export KIOKU_LITE_USER_ID={resolved_user_id}")
    typer.echo('  kioku-lite save "Hôm nay gặp Hùng ở café" --mood happy')
    typer.echo('  kioku-lite search "Hùng"')
    typer.echo("")
    typer.echo("For Claude Code / Cursor agents:")
    typer.echo("  kioku-lite init    # generates CLAUDE.md + SKILL.md")
    typer.echo("")


# ── init ───────────────────────────────────────────────────────────────────────

@app.command()
def init() -> None:
    """Generate CLAUDE.md + SKILL.md for Claude Code / Cursor agent integration."""
    RESOURCES = Path(__file__).parent / "resources"

    claude_dst = Path.cwd() / "CLAUDE.md"
    skill_dir = Path.cwd() / ".claude" / "skills" / "kioku-lite"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_dst = skill_dir / "SKILL.md"

    claude_src = RESOURCES / "CLAUDE.agent.md"
    skill_src = RESOURCES / "SKILL.md"

    if not claude_src.exists() or not skill_src.exists():
        typer.echo("⚠️  Resource files not found. Run `pip install kioku-agent-kit-lite[full]`", err=True)
        raise typer.Exit(1)

    claude_dst.write_text(claude_src.read_text(encoding="utf-8"))
    skill_dst.write_text(skill_src.read_text(encoding="utf-8"))

    typer.echo(f"✅ {claude_dst}")
    typer.echo(f"✅ {skill_dst}")
    typer.echo("")
    typer.echo("Agent is ready! Start Claude Code and ask it to remember things.")
    typer.echo("")


if __name__ == "__main__":
    app()
