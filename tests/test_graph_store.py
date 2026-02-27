"""Tests for GraphStore: nodes, edges, SAME_AS aliases, traversal, path finding."""

from __future__ import annotations

import pytest

from kioku_lite.pipeline.graph_store import GraphStore
from kioku_lite.pipeline.models import GraphEdge, GraphNode


def _add_node(graph: GraphStore, name: str, entity_type: str = "PERSON", date: str = "2026-02-27") -> None:
    graph.upsert_node(name, entity_type, date)


def _add_edge(graph: GraphStore, src: str, tgt: str, rel: str = "KNOWS", weight: float = 0.7, evidence: str = "", h: str = "") -> None:
    graph.upsert_edge(src, tgt, rel, weight, evidence, h)


# ── upsert_node ────────────────────────────────────────────────────────────────

class TestUpsertNode:
    def test_creates_node(self, graph):
        _add_node(graph, "Phúc", "PERSON")
        entities = graph.get_canonical_entities(limit=10)
        names = [e["name"] for e in entities]
        assert "Phúc" in names

    def test_mention_count_increments(self, graph):
        _add_node(graph, "Hùng")
        _add_node(graph, "Hùng")
        _add_node(graph, "Hùng")
        entities = graph.get_canonical_entities(limit=10)
        hùng = next(e for e in entities if e["name"] == "Hùng")
        assert hùng["mentions"] == 3

    def test_type_preserved(self, graph):
        _add_node(graph, "TBV", "ORGANIZATION")
        entities = graph.get_canonical_entities(limit=10)
        tbv = next(e for e in entities if e["name"] == "TBV")
        assert tbv["type"] == "ORGANIZATION"

    def test_ordered_by_mention_count(self, graph):
        _add_node(graph, "Major")
        _add_node(graph, "Major")
        _add_node(graph, "Major")
        _add_node(graph, "Minor")
        entities = graph.get_canonical_entities(limit=10)
        assert entities[0]["name"] == "Major"


# ── upsert_edge ────────────────────────────────────────────────────────────────

class TestUpsertEdge:
    def test_creates_edge(self, graph):
        _add_node(graph, "A")
        _add_node(graph, "B")
        _add_edge(graph, "A", "B", "KNOWS", 0.8, "A knows B", "hash001")
        result = graph.traverse("A")
        assert len(result.edges) >= 1
        assert result.edges[0].rel_type == "KNOWS"

    def test_weight_averaged_on_conflict(self, graph):
        _add_node(graph, "X")
        _add_node(graph, "Y")
        _add_edge(graph, "X", "Y", "KNOWS", 1.0, "first", "h1")
        _add_edge(graph, "X", "Y", "KNOWS", 0.0, "second", "h2")  # same src/tgt/rel → conflict
        result = graph.traverse("X")
        edges = [e for e in result.edges if e.rel_type == "KNOWS"]
        assert len(edges) == 1
        assert abs(edges[0].weight - 0.5) < 0.01  # averaged

    def test_source_hash_stored(self, graph):
        _add_node(graph, "P")
        _add_node(graph, "Q")
        _add_edge(graph, "P", "Q", "RELATES", 0.6, "p relates q", "myhash123")
        result = graph.traverse("P")
        assert any(e.source_hash == "myhash123" for e in result.edges)


# ── search_nodes ───────────────────────────────────────────────────────────────

class TestSearchNodes:
    def test_exact_match(self, graph):
        _add_node(graph, "Nguyễn Trọng Phúc")
        results = graph.search_nodes("Nguyễn Trọng Phúc")
        assert any(n.name == "Nguyễn Trọng Phúc" for n in results)

    def test_substring_match(self, graph):
        _add_node(graph, "Sinh nhật")
        _add_node(graph, "Nhật Bản")
        results = graph.search_nodes("Nhật")
        names = [n.name for n in results]
        assert "Nhật Bản" in names
        assert "Sinh nhật" in names

    def test_rerank_exact_first(self, graph):
        """'Nhật' should rank 'Nhật Bản' above 'Sinh nhật' (word boundary)."""
        _add_node(graph, "Sinh nhật")
        _add_node(graph, "Nhật Bản")
        _add_node(graph, "Nhật")
        results = graph.search_nodes("Nhật")
        # Exact match "Nhật" must come first
        assert results[0].name == "Nhật"

    def test_case_insensitive(self, graph):
        _add_node(graph, "TBV")
        results = graph.search_nodes("tbv")
        assert any(n.name == "TBV" for n in results)

    def test_no_match(self, graph):
        _add_node(graph, "SomeEntity")
        results = graph.search_nodes("xyznotfound")
        assert results == []


# ── add_alias / SAME_AS ────────────────────────────────────────────────────────

class TestAliases:
    def test_add_alias(self, graph):
        graph.add_alias("phuc-nt", "Nguyễn Trọng Phúc")
        entities = graph.get_canonical_entities(limit=50)
        phuc = next((e for e in entities if e["name"] == "Nguyễn Trọng Phúc"), None)
        assert phuc is not None
        assert "phuc-nt" in phuc["aliases"]

    def test_multiple_aliases(self, graph):
        for alias in ["Phúc", "anh", "phuc-nt", "tôi"]:
            graph.add_alias(alias, "Nguyễn Trọng Phúc")
        entities = graph.get_canonical_entities(limit=50)
        phuc = next(e for e in entities if e["name"] == "Nguyễn Trọng Phúc")
        assert len(phuc["aliases"]) == 4

    def test_alias_self_skip(self, graph):
        """Adding canonical as its own alias should not create duplicate."""
        graph.add_alias("Phúc", "Phúc")  # same name → should be a no-op for alias table
        entities = graph.get_canonical_entities(limit=50)
        phuc = next((e for e in entities if e["name"] == "Phúc"), None)
        # No self-alias should appear
        if phuc:
            assert "Phúc" not in phuc["aliases"]

    def test_traverse_follows_alias(self, graph):
        """Traversal from alias should find edges on canonical."""
        _add_node(graph, "Nguyễn Trọng Phúc")
        _add_node(graph, "LINE")
        _add_edge(graph, "Nguyễn Trọng Phúc", "LINE", "WORKS_AT", 0.9, "works at LINE", "h1")
        graph.add_alias("Phúc", "Nguyễn Trọng Phúc")

        result = graph.traverse("Phúc")  # search by alias
        names = {n.name for n in result.nodes}
        assert "LINE" in names

    def test_resolve_names_includes_canonical(self, graph):
        graph.add_alias("self", "Phúc")
        graph.add_alias("tôi", "Phúc")
        resolved = graph._resolve_names("self")
        # Should include both "self", "Phúc", and "tôi"
        resolved_lower = [n.lower() for n in resolved]
        assert "phúc" in resolved_lower
        assert "tôi" in resolved_lower


# ── traverse ───────────────────────────────────────────────────────────────────

class TestTraverse:
    def test_basic_traversal(self, graph):
        _add_node(graph, "Phúc")
        _add_node(graph, "TBV")
        _add_edge(graph, "Phúc", "TBV", "WORKS_AT", 0.9, "", "h1")
        result = graph.traverse("Phúc")
        node_names = {n.name for n in result.nodes}
        assert "TBV" in node_names

    def test_multi_hop(self, graph):
        _add_node(graph, "A")
        _add_node(graph, "B")
        _add_node(graph, "C")
        _add_edge(graph, "A", "B", "KNOWS", 0.8, "", "h1")
        _add_edge(graph, "B", "C", "KNOWS", 0.8, "", "h2")
        result = graph.traverse("A", max_hops=2)
        node_names = {n.name for n in result.nodes}
        assert "C" in node_names  # 2-hop

    def test_max_hops_1_stops_early(self, graph):
        _add_node(graph, "A")
        _add_node(graph, "B")
        _add_node(graph, "C")
        _add_edge(graph, "A", "B", "KNOWS", 0.8, "", "h1")
        _add_edge(graph, "B", "C", "KNOWS", 0.8, "", "h2")
        result = graph.traverse("A", max_hops=1)
        node_names = {n.name for n in result.nodes}
        assert "C" not in node_names  # 2-hops away, blocked

    def test_empty_graph_returns_empty(self, graph):
        result = graph.traverse("NonExistent")
        assert result.nodes == []
        assert result.edges == []

    def test_edges_deduped(self, graph):
        _add_node(graph, "X")
        _add_node(graph, "Y")
        _add_edge(graph, "X", "Y", "KNOWS", 0.8, "e1", "h1")
        result = graph.traverse("X")
        # Should not have duplicate edges
        edge_keys = [f"{e.source}|{e.target}|{e.rel_type}|{e.source_hash}" for e in result.edges]
        assert len(edge_keys) == len(set(edge_keys))


# ── find_path ──────────────────────────────────────────────────────────────────

class TestFindPath:
    def test_direct_connection(self, graph):
        _add_node(graph, "Phúc")
        _add_node(graph, "LINE")
        _add_edge(graph, "Phúc", "LINE", "WORKS_AT", 0.9, "", "h1")
        result = graph.find_path("Phúc", "LINE")
        assert result.connected is True if hasattr(result, 'connected') else len(result.paths) > 0

    def test_indirect_connection(self, graph):
        _add_node(graph, "A")
        _add_node(graph, "B")
        _add_node(graph, "C")
        _add_edge(graph, "A", "B", "KNOWS", 0.8, "", "h1")
        _add_edge(graph, "B", "C", "KNOWS", 0.8, "", "h2")
        result = graph.find_path("A", "C")
        assert len(result.paths) > 0
        path = result.paths[0]
        assert path[0] == "A"
        assert path[-1] == "C"

    def test_no_connection(self, graph):
        _add_node(graph, "Island1")
        _add_node(graph, "Island2")
        result = graph.find_path("Island1", "Island2")
        assert len(result.paths) == 0

    def test_path_length(self, graph):
        for name in ["A", "B", "C", "D"]:
            _add_node(graph, name)
        _add_edge(graph, "A", "B", "KNOWS", 0.8, "", "h1")
        _add_edge(graph, "B", "C", "KNOWS", 0.8, "", "h2")
        _add_edge(graph, "C", "D", "KNOWS", 0.8, "", "h3")
        result = graph.find_path("A", "D")
        assert len(result.paths) > 0
        assert len(result.paths[0]) == 4  # A-B-C-D


# ── get_canonical_entities ─────────────────────────────────────────────────────

class TestGetCanonicalEntities:
    def test_returns_entities_with_aliases(self, graph):
        _add_node(graph, "Phúc")
        graph.add_alias("tôi", "Phúc")
        entities = graph.get_canonical_entities(limit=10)
        phuc = next(e for e in entities if e["name"] == "Phúc")
        assert "tôi" in phuc["aliases"]

    def test_limit_respected(self, graph):
        for i in range(20):
            _add_node(graph, f"Entity{i}")
        entities = graph.get_canonical_entities(limit=5)
        assert len(entities) <= 5

    def test_empty_graph(self, graph):
        assert graph.get_canonical_entities() == []
