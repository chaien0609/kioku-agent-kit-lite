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


# ── users ──────────────────────────────────────────────────────────────────────

@app.command()
def users(
    create: Optional[str] = typer.Option(None, "--create", "-c", help="Create a new profile with this ID."),
) -> None:
    """List all user profiles, or create a new one.

    At the start of each session, the agent should run this command to show
    the user their available profiles, then ask which one to use.

    \b
    # List all profiles:
    kioku-lite users

    # Create a new profile:
    kioku-lite users --create work
    """
    base_dir = Path.home() / ".kioku-lite" / "users"

    if create:
        # Validate name
        if not create.replace("-", "").replace("_", "").isalnum():
            typer.echo("⚠️  Profile ID can only contain letters, numbers, hyphens and underscores.", err=True)
            raise typer.Exit(1)
        profile_dir = base_dir / create / "data"
        profile_dir.mkdir(parents=True, exist_ok=True)
        memory_dir = base_dir / create / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        result = {"status": "created", "user_id": create, "path": str(base_dir / create)}
        _out(result)
        typer.echo(f"\nTo use this profile: KIOKU_LITE_USER_ID={create} kioku-lite save \"...\"")
        return

    # Ensure default profile "personal" always exists
    default_dir = base_dir / "personal" / "data"
    default_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "personal" / "memory").mkdir(parents=True, exist_ok=True)

    # Scan filesystem — directories = profiles
    profiles = []
    if base_dir.exists():
        for p in sorted(base_dir.iterdir()):
            if p.is_dir():
                db = p / "data" / "kioku.db"
                profiles.append({
                    "user_id": p.name,
                    "has_data": db.exists(),
                    "db_size_kb": round(db.stat().st_size / 1024, 1) if db.exists() else 0,
                })

    _out({"profiles": profiles, "hint": "Use KIOKU_LITE_USER_ID=<user_id> prefix to switch profiles"})


# ── setup ──────────────────────────────────────────────────────────────────────

@app.command()
def setup(
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="Your user ID (default: personal)."),
) -> None:
    """First-time setup: create config and download embedding model (no Docker needed).

    The FastEmbed model (intfloat/multilingual-e5-large, ~1.1GB) is downloaded once
    to ~/.cache/fastembed/ and reused on all subsequent runs. No Docker required.
    """
    resolved_user_id = user_id or os.environ.get("KIOKU_LITE_USER_ID", "personal")
    embed_model = "intfloat/multilingual-e5-large"

    typer.echo("")
    typer.echo("╔══════════════════════════════════════╗")
    typer.echo("║   Kioku Agent Kit Lite — Setup       ║")
    typer.echo("║   Zero Docker · Zero Cloud LLM       ║")
    typer.echo("╚══════════════════════════════════════╝")
    typer.echo("")
    typer.echo(f"User ID     : {resolved_user_id}")
    typer.echo(f"Embed model : {embed_model} (FastEmbed ONNX)")
    typer.echo("")

    # Step 1: Config file
    typer.echo("── Step 1: Configuration ──")
    config_dir = Path.home() / ".kioku-lite"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.env"

    if config_file.exists():
        typer.echo(f"  ✅ Config exists: {config_file}")
    else:
        from datetime import date
        config_file.write_text(
            f"""# Kioku Agent Kit Lite — Configuration
# Generated: {date.today()}

KIOKU_LITE_USER_ID={resolved_user_id}

# Embedding: FastEmbed ONNX — runs 100% local, no Docker
KIOKU_LITE_EMBED_PROVIDER=fastembed
KIOKU_LITE_EMBED_MODEL={embed_model}
KIOKU_LITE_EMBED_DIM=1024

# Set EMBED_PROVIDER=fake to skip model download (BM25 + Graph only):
# KIOKU_LITE_EMBED_PROVIDER=fake
""",
            encoding="utf-8",
        )
        typer.echo(f"  ✅ Created: {config_file}")

    # Step 2: Download embedding model
    typer.echo("")
    typer.echo(f"── Step 2: Embedding model ({embed_model}) ──")
    typer.echo("   Downloading ~1.1GB to ~/.cache/fastembed/ (once only)...")
    try:
        from kioku_lite.pipeline.embedder import FastEmbedder
        embedder = FastEmbedder(model_name=embed_model)
        embedder.embed("warmup")
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
def init(
    global_: bool = typer.Option(
        False, "--global", "-g",
        help="Install globally into ~/.claude/ — works in ALL projects without re-running init.",
    ),
) -> None:
    """Generate CLAUDE.md + SKILL.md for Claude Code / Cursor agent integration.

    By default: writes to the current project directory.

    With --global: installs SKILL.md into ~/.claude/skills/kioku-lite/SKILL.md
    so Claude Code picks it up in EVERY project automatically. Recommended.

    \b
    # One-time global setup (recommended):
    kioku-lite init --global

    # Per-project setup (if you want project-specific):
    kioku-lite init
    """
    RESOURCES = Path(__file__).parent / "resources"

    claude_src = RESOURCES / "CLAUDE.agent.md"
    skill_src = RESOURCES / "SKILL.md"

    if not claude_src.exists() or not skill_src.exists():
        typer.echo("⚠️  Resource files not found. Reinstall: pip install 'kioku-lite[cli]'", err=True)
        raise typer.Exit(1)

    if global_:
        # Write to ~/.claude/ — Claude Code reads this from any project
        skill_dir = Path.home() / ".claude" / "skills" / "kioku-lite"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_dst = skill_dir / "SKILL.md"
        skill_dst.write_text(skill_src.read_text(encoding="utf-8"))

        typer.echo("")
        typer.echo("✅ Global install:")
        typer.echo(f"   {skill_dst}")
        typer.echo("")
        typer.echo("Claude Code will now use kioku-lite in EVERY project automatically.")
        typer.echo("No need to run `kioku-lite init` per project.")
        typer.echo("")
        typer.echo("Note: No CLAUDE.md is written globally — Claude reads SKILL.md via")
        typer.echo("      the skills directory. To also add a CLAUDE.md to a specific")
        typer.echo("      project, run `kioku-lite init` (without --global) there.")
        typer.echo("")
    else:
        # Write to current project directory
        claude_dst = Path.cwd() / "CLAUDE.md"
        skill_dir = Path.cwd() / ".claude" / "skills" / "kioku-lite"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_dst = skill_dir / "SKILL.md"

        claude_dst.write_text(claude_src.read_text(encoding="utf-8"))
        skill_dst.write_text(skill_src.read_text(encoding="utf-8"))

        typer.echo("")
        typer.echo("✅ Project install:")
        typer.echo(f"   {claude_dst}")
        typer.echo(f"   {skill_dst}")
        typer.echo("")
        typer.echo("Claude Code will use kioku-lite in THIS project.")
        typer.echo("")
        typer.echo("Tip: Run `kioku-lite init --global` once to enable in ALL projects.")
        typer.echo("")



if __name__ == "__main__":
    app()
