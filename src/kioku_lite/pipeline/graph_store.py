"""Knowledge Graph store — SQLite-backed entity nodes, edges, and traversal.

Tables: kg_nodes, kg_edges, kg_aliases
No Cypher, no FalkorDB — pure Python BFS on top of SQLite.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import deque

from kioku_lite.pipeline.models import GraphEdge, GraphNode, GraphSearchResult

log = logging.getLogger(__name__)


class GraphStore:
    """Knowledge graph backed by three SQLite tables.

    Shares a sqlite3.Connection with MemoryStore (created by KiokuDB).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ── Upsert ─────────────────────────────────────────────────────────────────

    def upsert_node(self, name: str, entity_type: str, date: str) -> None:
        """Insert or update entity node, incrementing mention_count."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO kg_nodes (name, type, mention_count, first_seen, last_seen)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                mention_count = mention_count + 1,
                last_seen = excluded.last_seen,
                type = CASE WHEN excluded.type != '' THEN excluded.type ELSE type END
            """,
            (name, entity_type, date, date),
        )
        self.conn.commit()

    def upsert_edge(
        self,
        source: str,
        target: str,
        rel_type: str,
        weight: float,
        evidence: str,
        source_hash: str,
        event_time: str = "",
    ) -> None:
        """Insert or update relationship edge, averaging weights on conflict."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO kg_edges (source, target, rel_type, weight, evidence, source_hash, event_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, target, rel_type) DO UPDATE SET
                weight = (weight + excluded.weight) / 2,
                evidence = excluded.evidence,
                source_hash = excluded.source_hash,
                event_time = excluded.event_time
            """,
            (source, target, rel_type, weight, evidence, source_hash, event_time),
        )
        self.conn.commit()

    def add_alias(self, alias: str, canonical: str) -> None:
        """Register an alias → canonical SAME_AS mapping."""
        cur = self.conn.cursor()
        for name in (alias, canonical):
            cur.execute(
                "INSERT OR IGNORE INTO kg_nodes (name, type, mention_count) VALUES (?, 'PERSON', 0)",
                (name,),
            )
        cur.execute("UPDATE kg_nodes SET is_canonical = 1 WHERE name = ?", (canonical,))
        cur.execute(
            "INSERT OR IGNORE INTO kg_aliases (alias, canonical) VALUES (?, ?)",
            (alias, canonical),
        )
        self.conn.commit()
        log.info("Linked alias '%s' → canonical '%s'", alias, canonical)

    # ── Query ──────────────────────────────────────────────────────────────────

    def get_canonical_entities(self, limit: int = 50) -> list[dict]:
        """Top entities by mention_count, with their aliases included."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT n.name, n.type, n.mention_count,
                   GROUP_CONCAT(a.alias, '|||') AS aliases
            FROM kg_nodes n
            LEFT JOIN kg_aliases a ON a.canonical = n.name COLLATE NOCASE
            GROUP BY n.name
            ORDER BY n.mention_count DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "name": r[0],
                "type": r[1] or "",
                "mentions": r[2] or 0,
                "aliases": [x for x in (r[3] or "").split("|||") if x],
            }
            for r in cur.fetchall()
        ]

    def search_nodes(self, query: str, limit: int = 30) -> list[GraphNode]:
        """Case-insensitive substring search, re-ranked by match quality."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT name, type, mention_count, first_seen, last_seen
            FROM kg_nodes
            WHERE name LIKE ? COLLATE NOCASE
            ORDER BY mention_count DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        )
        nodes = [
            GraphNode(
                name=r[0], type=r[1] or "", mention_count=r[2] or 0,
                first_seen=r[3] or "", last_seen=r[4] or "",
            )
            for r in cur.fetchall()
        ]
        return self._rerank_nodes(nodes, query)

    @staticmethod
    def _rerank_nodes(nodes: list[GraphNode], query: str) -> list[GraphNode]:
        """Re-rank nodes: exact > starts-with > whole-word > substring."""
        q = query.lower()
        is_single = " " not in q.strip()

        def _key(n: GraphNode) -> tuple:
            nl = n.name.lower()
            if nl == q:
                return (0, -n.mention_count)
            if nl.startswith(q + " ") or (not is_single and nl.endswith(" " + q)):
                return (1, -n.mention_count)
            if q + " " in nl or " " + q in nl:
                return (2, -n.mention_count)
            if is_single and nl.endswith(" " + q):
                return (2, -n.mention_count)
            return (3, -n.mention_count)

        nodes.sort(key=_key)
        return nodes

    # ── Traversal ──────────────────────────────────────────────────────────────

    def traverse(self, entity_name: str, max_hops: int = 2, limit: int = 20) -> GraphSearchResult:
        """BFS traversal from seed entity, following SAME_AS aliases."""
        seeds = self._resolve_names(entity_name)
        nodes_map: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []
        seen: set[str] = set()

        for seed in seeds:
            self._bfs(seed, max_hops, limit, nodes_map, edges, seen)

        return GraphSearchResult(nodes=list(nodes_map.values()), edges=edges[:limit])

    def _resolve_names(self, name: str) -> list[str]:
        """Expand a name to include its canonical and all known aliases."""
        names: dict[str, str] = {name.lower(): name}
        cur = self.conn.cursor()
        # alias → find canonical
        cur.execute("SELECT canonical FROM kg_aliases WHERE alias = ? COLLATE NOCASE", (name,))
        for row in cur.fetchall():
            names[row[0].lower()] = row[0]
        # canonical → find all aliases
        for n in list(names.values()):
            cur.execute("SELECT alias FROM kg_aliases WHERE canonical = ? COLLATE NOCASE", (n,))
            for row in cur.fetchall():
                if row[0].lower() not in names:
                    names[row[0].lower()] = row[0]
        return list(names.values())

    def _bfs(
        self,
        start: str,
        max_hops: int,
        limit: int,
        nodes_map: dict[str, GraphNode],
        edges: list[GraphEdge],
        seen: set[str],
    ) -> None:
        """BFS from start, collecting up to `limit` edges."""
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        visited: set[str] = {start.lower()}
        cur = self.conn.cursor()

        while queue and len(edges) < limit:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue
            cur.execute(
                """
                SELECT source, target, rel_type, weight, evidence, source_hash
                FROM kg_edges
                WHERE source = ? COLLATE NOCASE OR target = ? COLLATE NOCASE
                ORDER BY weight DESC LIMIT 50
                """,
                (current, current),
            )
            for row in cur.fetchall():
                src, tgt, rel, weight, evidence, src_hash = row
                key = f"{src.lower()}|{tgt.lower()}|{rel}|{src_hash}"
                if key not in seen:
                    seen.add(key)
                    edges.append(GraphEdge(
                        source=src, target=tgt, rel_type=rel,
                        weight=weight, evidence=evidence or "", source_hash=src_hash or "",
                    ))
                    nodes_map[src.lower()] = GraphNode(name=src, type="")
                    nodes_map[tgt.lower()] = GraphNode(name=tgt, type="")
                    neighbor = tgt if src.lower() == current.lower() else src
                    if neighbor.lower() not in visited:
                        visited.add(neighbor.lower())
                        queue.append((neighbor, depth + 1))

        # Enrich nodes with metadata
        self._enrich_nodes(nodes_map)

    def _enrich_nodes(self, nodes_map: dict[str, GraphNode]) -> None:
        """Fill in type/mention_count/dates for collected nodes."""
        cur = self.conn.cursor()
        for key, node in list(nodes_map.items()):
            cur.execute(
                "SELECT name, type, mention_count, first_seen, last_seen "
                "FROM kg_nodes WHERE name = ? COLLATE NOCASE",
                (node.name,),
            )
            row = cur.fetchone()
            if row:
                nodes_map[key] = GraphNode(
                    name=row[0], type=row[1] or "", mention_count=row[2] or 0,
                    first_seen=row[3] or "", last_seen=row[4] or "",
                )

    def find_path(self, source: str, target: str) -> GraphSearchResult:
        """BFS shortest path between two entities (undirected)."""
        cur = self.conn.cursor()
        cur.execute("SELECT source, target, rel_type, evidence FROM kg_edges")
        adj: dict[str, list[tuple[str, str, str]]] = {}
        for row in cur.fetchall():
            s, t, rel, ev = row[0], row[1], row[2] or "", row[3] or ""
            adj.setdefault(s.lower(), []).append((t, rel, ev))
            adj.setdefault(t.lower(), []).append((s, rel, ev))

        queue: deque[tuple[str, list[str]]] = deque([(source.lower(), [source])])
        visited = {source.lower()}

        while queue:
            current, path = queue.popleft()
            if current == target.lower():
                nodes = [GraphNode(name=n, type="") for n in path]
                edges = []
                for i in range(len(path) - 1):
                    a, b = path[i].lower(), path[i + 1].lower()
                    for nb, rel, ev in adj.get(a, []):
                        if nb.lower() == b:
                            edges.append(GraphEdge(source=path[i], target=path[i + 1], rel_type=rel, evidence=ev))
                            break
                return GraphSearchResult(nodes=nodes, edges=edges, paths=[path])
            for neighbor, _, _ in adj.get(current, []):
                if neighbor.lower() not in visited:
                    visited.add(neighbor.lower())
                    queue.append((neighbor.lower(), path + [neighbor]))

        return GraphSearchResult()
