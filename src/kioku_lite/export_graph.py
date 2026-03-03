"""Graph export utilities — HTML (pyvis) and JSON (D3 node-link).

Usage from CLI:
    kioku-lite export-graph [OUTPUT] --format html   # default
    kioku-lite export-graph [OUTPUT] --format json
"""

from __future__ import annotations

import json
from pathlib import Path

# ── Color palette ────────────────────────────────────────────────────────────

# Predefined colors for known entity types (matches kioku design accent palette)
_TYPE_COLORS: dict[str, str] = {
    "EMOTION": "#e94560",
    "LIFE_EVENT": "#9b59b6",
    "DECISION": "#D97757",  # kioku accent
    "LESSON": "#1abc9c",
    "PERSON": "#4287f5",
    "PEOPLE": "#4287f5",
    "TOPIC": "#95a5a6",
    "PROJECT": "#2ecc71",
    "ORGANIZATION": "#3498db",
    "ORG": "#3498db",
    "PLACE": "#f1c40f",
    "LOCATION": "#f39c12",
    "CONCEPT": "#e67e22",
    "TASK": "#16a085",
    "EVENT": "#8e44ad",
}

_FALLBACK_PALETTE = [
    "#e74c3c", "#e67e22", "#f39c12", "#27ae60",
    "#2980b9", "#8e44ad", "#16a085", "#c0392b",
]

_type_color_cache: dict[str, str] = {}
_fallback_index = 0


def _color_for_type(entity_type: str) -> str:
    """Return a consistent color for the given entity type."""
    global _fallback_index
    key = entity_type.upper()
    if key in _TYPE_COLORS:
        return _TYPE_COLORS[key]
    if key not in _type_color_cache:
        _type_color_cache[key] = _FALLBACK_PALETTE[_fallback_index % len(_FALLBACK_PALETTE)]
        _fallback_index += 1
    return _type_color_cache[key]


# ── JSON export (D3 node-link) ───────────────────────────────────────────────

def export_json(graph_data: dict, output_path: str | Path) -> Path:
    """Export graph as D3 node-link JSON.

    Format:
        {
          "nodes": [{"id": "Alice", "name": "Alice", "type": "PERSON", ...}],
          "links": [{"source": "Alice", "target": "Bob", "relation": "KNOWS", ...}]
        }

    Args:
        graph_data: Output of KiokuLiteService.get_graph_data()
        output_path: Destination file path (e.g. "graph.json")

    Returns:
        Resolved Path of the written file.
    """
    out = Path(output_path).resolve()
    with open(out, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)
    return out


# ── HTML export (pyvis) ──────────────────────────────────────────────────────

def export_html(graph_data: dict, output_path: str | Path, title: str = "Kioku Knowledge Graph") -> Path:
    """Export graph as standalone interactive HTML using pyvis (vis-network).

    Requires: pip install pyvis  (or kioku-lite[export])

    Features:
        - Fully offline (JS embedded inline via cdn_resources='in_line')
        - Nodes colored by entity type
        - Node size proportional to mention_count
        - Edge labels show rel_type
        - Physics simulation (Barnes-Hut), drag/zoom/hover

    Args:
        graph_data: Output of KiokuLiteService.get_graph_data()
        output_path: Destination file path (e.g. "graph.html")
        title: HTML page title shown in browser tab

    Returns:
        Resolved Path of the written file.

    Raises:
        ImportError: If pyvis is not installed.
    """
    try:
        from pyvis.network import Network  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "pyvis is required for HTML export.\n"
            "Install it with:  pip install pyvis\n"
            "Or:               pip install \"kioku-lite[export]\""
        ) from exc

    nodes: list[dict] = graph_data.get("nodes", [])
    links: list[dict] = graph_data.get("links", [])

    if not nodes:
        raise ValueError("No entities found in the knowledge graph. Save some memories and run kg-index first.")

    net = Network(
        height="100vh",
        width="100%",
        directed=True,
        cdn_resources="in_line",  # fully offline — embeds vis-network JS inline
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        heading="",  # empty — pyvis duplicates heading as visible h1 + <title>
    )

    # Physics: Barnes-Hut gives good spacing for medium graphs
    net.barnes_hut(
        gravity=-6000,
        central_gravity=0.25,
        spring_length=150,
        spring_strength=0.05,
        damping=0.09,
    )

    # Add nodes
    node_ids: set[str] = set()
    for node in nodes:
        nid = node["id"]
        name = node["name"]
        entity_type = node.get("type") or "UNKNOWN"
        mentions = node.get("mentions", 0)
        first_seen = node.get("first_seen", "")
        last_seen = node.get("last_seen", "")
        aliases = node.get("aliases", [])

        color = _color_for_type(entity_type)
        # Node size: base 15, grow with mentions (capped)
        size = min(15 + mentions * 3, 60)

        tooltip_parts = [f"<b>{name}</b>", f"Type: {entity_type}", f"Mentions: {mentions}"]
        if first_seen:
            tooltip_parts.append(f"First seen: {first_seen}")
        if last_seen:
            tooltip_parts.append(f"Last seen: {last_seen}")
        if aliases:
            tooltip_parts.append(f"Aliases: {', '.join(aliases)}")
        tooltip = "<br>".join(tooltip_parts)

        net.add_node(
            nid,
            label=name,
            title=tooltip,
            color={"background": color, "border": color, "highlight": {"background": "#ffffff", "border": color}},
            size=size,
            font={"color": "#ffffff", "size": 12},
            borderWidth=1,
        )
        node_ids.add(nid)

    # Add edges (skip if either endpoint not in node set)
    for link in links:
        src = link["source"]
        tgt = link["target"]
        if src not in node_ids or tgt not in node_ids:
            continue

        rel = link.get("relation", "")
        weight = link.get("weight", 0.5)
        evidence = link.get("evidence", "")

        tooltip_parts = [f"<b>{rel}</b>", f"Weight: {weight:.2f}"]
        if evidence:
            tooltip_parts.append(f"Evidence: {evidence[:120]}{'...' if len(evidence) > 120 else ''}")
        edge_tooltip = "<br>".join(tooltip_parts)

        net.add_edge(
            src,
            tgt,
            title=edge_tooltip,
            label=rel,
            width=max(1.0, weight * 3),
            color={"color": "rgba(200,200,200,0.4)", "highlight": "#D97757"},
            font={"color": "#aaaaaa", "size": 9, "align": "middle"},
            arrows={"to": {"enabled": True, "scaleFactor": 0.6}},
            smooth={"type": "curvedCW", "roundness": 0.1},
        )

    out = Path(output_path).resolve()
    net.show(str(out), notebook=False)
    return out
