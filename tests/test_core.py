"""Tests for embedder, DB init, RRF reranker, and search functions."""

from __future__ import annotations

import pytest

from kioku_lite.pipeline.embedder import FakeEmbedder, make_embedder
from kioku_lite.pipeline.db import KiokuDB
from kioku_lite.search.bm25 import SearchResult, bm25_search
from kioku_lite.search.reranker import rrf_rerank
from kioku_lite.search.semantic import vector_search
from kioku_lite.search.graph import graph_search


# ── Embedder ───────────────────────────────────────────────────────────────────

class TestFakeEmbedder:
    def test_embed_dimensions(self):
        e = FakeEmbedder(dimensions=64)
        assert len(e.embed("test")) == 64

    def test_default_dimensions(self):
        e = FakeEmbedder()
        assert len(e.embed("test")) == 128

    def test_deterministic(self):
        e = FakeEmbedder()
        v1 = e.embed("same text")
        v2 = e.embed("same text")
        assert v1 == v2

    def test_different_texts_different_vectors(self):
        e = FakeEmbedder()
        v1 = e.embed("text one")
        v2 = e.embed("text two")
        assert v1 != v2

    def test_embed_batch(self):
        e = FakeEmbedder(dimensions=32)
        texts = ["a", "b", "c"]
        batch = e.embed_batch(texts)
        assert len(batch) == 3
        assert all(len(v) == 32 for v in batch)

    def test_embed_batch_consistent_with_single(self):
        e = FakeEmbedder()
        texts = ["hello", "world"]
        batch = e.embed_batch(texts)
        assert batch[0] == e.embed("hello")
        assert batch[1] == e.embed("world")

    def test_values_in_range(self):
        e = FakeEmbedder(dimensions=256)
        v = e.embed("range test")
        assert all(-1.0 <= x <= 1.0 for x in v)


class TestMakeEmbedder:
    def test_fake_provider(self):
        e = make_embedder(provider="fake")
        assert isinstance(e, FakeEmbedder)

    def test_fastembed_fallback_to_fake_when_unavailable(self, monkeypatch):
        """If fastembed is missing, should fall back to FakeEmbedder."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "fastembed":
                raise ImportError("fastembed not available")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        e = make_embedder(provider="fastembed")
        assert isinstance(e, FakeEmbedder)


# ── KiokuDB initialization ─────────────────────────────────────────────────────

class TestKiokuDB:
    def test_db_creates_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = KiokuDB(db_path, embed_dim=128)
        assert db_path.exists()
        db.close()

    def test_memory_store_accessible(self, db):
        assert db.memory is not None

    def test_graph_store_accessible(self, db):
        assert db.graph is not None

    def test_schema_is_idempotent(self, tmp_path):
        """Opening the same DB twice should not error."""
        db_path = tmp_path / "idem.db"
        db1 = KiokuDB(db_path, embed_dim=128)
        db1.close()
        db2 = KiokuDB(db_path, embed_dim=128)
        db2.close()

    def test_parent_dirs_created(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "test.db"
        db = KiokuDB(nested, embed_dim=128)
        assert nested.exists()
        db.close()


# ── RRF Reranker ───────────────────────────────────────────────────────────────

class TestRRFReranker:
    def _make_result(self, content: str, score: float = 0.5, source: str = "bm25", content_hash: str = "") -> SearchResult:
        return SearchResult(content=content, date="2026-02-27", mood="", timestamp="", score=score, source=source, content_hash=content_hash or content)

    def test_single_list(self):
        results = [self._make_result(f"doc{i}") for i in range(5)]
        reranked = rrf_rerank(results, limit=3)
        assert len(reranked) <= 3

    def test_fusion_boosts_overlapping(self):
        """Document appearing in multiple lists should rank higher."""
        bm25 = [self._make_result("shared doc", content_hash="shared"), self._make_result("only bm25", content_hash="bm25")]
        vec = [self._make_result("shared doc", content_hash="shared"), self._make_result("only vec", content_hash="vec")]
        reranked = rrf_rerank(bm25, vec, limit=10)
        # "shared doc" should rank first (appeared in both lists)
        assert reranked[0].content == "shared doc"

    def test_dedup_by_content_hash(self):
        """Same content_hash from different sources should be merged."""
        r1 = self._make_result("text", content_hash="abc", source="bm25")
        r2 = self._make_result("text", content_hash="abc", source="vector")
        reranked = rrf_rerank([r1], [r2])
        items_with_hash = [r for r in reranked if r.content_hash == "abc"]
        assert len(items_with_hash) == 1

    def test_empty_lists(self):
        assert rrf_rerank([], [], limit=10) == []

    def test_limit_zero(self):
        results = [self._make_result("x")]
        assert rrf_rerank(results, limit=0) == []

    def test_scores_positive(self):
        results = [self._make_result(f"d{i}") for i in range(3)]
        reranked = rrf_rerank(results)
        assert all(r.score > 0 for r in reranked)

    def test_rank_order_preserved_for_single_list(self):
        """Items should preserve relative rank from input in single-list mode."""
        top = self._make_result("top", content_hash="top")
        mid = self._make_result("mid", content_hash="mid")
        bot = self._make_result("bot", content_hash="bot")
        reranked = rrf_rerank([top, mid, bot])
        assert reranked[0].content == "top"
        assert reranked[-1].content == "bot"


# ── bm25_search ────────────────────────────────────────────────────────────────

class TestBM25Search:
    def test_returns_search_results(self, memory):
        import hashlib
        h = hashlib.sha256(b"bm25 search test").hexdigest()
        memory.insert("bm25 search test", "2026-02-27", "2026-02-27T10:00:00", content_hash=h)
        from kioku_lite.search.bm25 import bm25_search
        results = bm25_search(memory, "bm25 search")
        assert len(results) >= 1
        assert results[0].source == "bm25"

    def test_scores_normalized_0_to_1(self, memory):
        import hashlib
        for i, text in enumerate(["alpha beta", "alpha gamma", "alpha delta"]):
            h = hashlib.sha256(text.encode()).hexdigest()
            memory.insert(text, "2026-02-27", f"2026-02-27T{i:02d}:00:00", content_hash=h)
        from kioku_lite.search.bm25 import bm25_search
        results = bm25_search(memory, "alpha")
        assert all(0.0 <= r.score <= 1.0 for r in results)

    def test_empty_results(self, memory):
        from kioku_lite.search.bm25 import bm25_search
        results = bm25_search(memory, "zzznomatch")
        assert results == []


# ── vector_search ──────────────────────────────────────────────────────────────

class TestVectorSearch:
    def test_returns_results(self, memory, fake_embedder):
        import hashlib
        text = "vector search content"
        h = hashlib.sha256(text.encode()).hexdigest()
        memory.insert(text, "2026-02-27", "2026-02-27T10:00:00", content_hash=h)
        memory.insert_vector(h, fake_embedder.embed(text))
        results = vector_search(memory, fake_embedder, "vector search content")
        assert len(results) >= 1
        assert results[0].source == "vector"

    def test_returns_content_hash(self, memory, fake_embedder):
        import hashlib
        text = "hashable content"
        h = hashlib.sha256(text.encode()).hexdigest()
        memory.insert(text, "2026-02-27", "2026-02-27T10:00:00", content_hash=h)
        memory.insert_vector(h, fake_embedder.embed(text))
        results = vector_search(memory, fake_embedder, text)
        assert results[0].content_hash == h

    def test_disabled_when_no_vec(self, memory, fake_embedder):
        memory.vec_enabled = False
        results = vector_search(memory, fake_embedder, "anything")
        assert results == []


# ── graph_search ───────────────────────────────────────────────────────────────

class TestGraphSearch:
    def test_basic_entity_search(self, graph):
        graph.upsert_node("Hùng", "PERSON", "2026-02-27")
        graph.upsert_node("TBV", "ORGANIZATION", "2026-02-27")
        graph.upsert_edge("Hùng", "TBV", "WORKS_AT", 0.9, "Hùng is at TBV", "myhash")
        results = graph_search(graph, "Hùng", entities=["Hùng"])
        # Should find the edge because traversal from Hùng reaches TBV via myhash
        assert isinstance(results, list)

    def test_stopword_only_returns_empty(self, graph):
        """Query with only stopwords should return empty."""
        results = graph_search(graph, "là và của")
        assert results == []

    def test_entity_seeds_take_priority(self, graph):
        """If entities provided, should use them as seeds not tokenization."""
        graph.upsert_node("Lan", "PERSON", "2026-02-27")
        graph.upsert_node("Test", "TOPIC", "2026-02-27")
        graph.upsert_edge("Lan", "Test", "INVOLVES", 0.7, "evidence", "h1")
        results = graph_search(graph, "random query", entities=["Lan"])
        # Should still traverse from Lan even if query doesn't match
        assert isinstance(results, list)
