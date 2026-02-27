"""Tests for MemoryStore: FTS5 BM25, sqlite-vec vector, CRUD."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from kioku_lite.pipeline.memory_store import MemoryStore


def _insert(memory: MemoryStore, content: str, date: str = "2026-02-27", mood: str = "") -> str:
    import hashlib
    h = hashlib.sha256(content.encode()).hexdigest()
    memory.insert(content=content, date=date, timestamp=f"{date}T10:00:00", mood=mood, content_hash=h)
    return h


# ── insert ─────────────────────────────────────────────────────────────────────

class TestInsert:
    def test_insert_returns_rowid(self, memory):
        rowid = memory.insert("hello world", "2026-02-27", "2026-02-27T10:00:00")
        assert rowid > 0

    def test_duplicate_skipped(self, memory):
        import hashlib
        h = hashlib.sha256(b"dedupe me").hexdigest()
        r1 = memory.insert("dedupe me", "2026-02-27", "2026-02-27T10:00:00", content_hash=h)
        r2 = memory.insert("dedupe me", "2026-02-27", "2026-02-27T10:00:00", content_hash=h)
        assert r1 > 0
        assert r2 == -1  # duplicate

    def test_count_increments(self, memory):
        assert memory.count() == 0
        _insert(memory, "first")
        assert memory.count() == 1
        _insert(memory, "second")
        assert memory.count() == 2


# ── FTS5 BM25 ─────────────────────────────────────────────────────────────────

class TestFTS5:
    def test_basic_search(self, memory):
        _insert(memory, "Hôm nay gặp Hùng tại TBV")
        results = memory.search_fts("Hùng", limit=5)
        assert len(results) == 1
        assert "Hùng" in results[0].content

    def test_no_match_returns_empty(self, memory):
        _insert(memory, "completely unrelated text")
        assert memory.search_fts("xyzzy_nonexistent") == []

    def test_multi_document_ranking(self, memory):
        _insert(memory, "Hùng rất vui vẻ")
        _insert(memory, "Hùng Hùng Hùng đến ba lần")  # higher BM25 score
        _insert(memory, "ngày bình thường không có Hùng")
        results = memory.search_fts("Hùng", limit=3)
        assert len(results) == 3
        # "Hùng Hùng Hùng" should rank highest
        assert "Hùng Hùng Hùng" in results[0].content

    def test_special_chars_safe(self, memory):
        """FTS5 special chars must not throw OperationalError."""
        _insert(memory, "Tech-Verse 2025: AI & ML event")
        results = memory.search_fts("Tech-Verse 2025")
        assert len(results) >= 1

    def test_vietnamese_text(self, memory):
        _insert(memory, "Hôm nay tôi đã đi làm và cảm thấy rất vui")
        results = memory.search_fts("vui")
        assert len(results) == 1

    def test_result_has_content_hash(self, memory):
        import hashlib
        h = hashlib.sha256(b"test hash").hexdigest()
        memory.insert("test hash", "2026-02-27", "2026-02-27T10:00:00", content_hash=h)
        results = memory.search_fts("test hash")
        assert results[0].content_hash == h

    def test_limit_respected(self, memory):
        for i in range(10):
            _insert(memory, f"matching document number {i}")
        results = memory.search_fts("matching document", limit=3)
        assert len(results) <= 3


# ── sqlite-vec ─────────────────────────────────────────────────────────────────

class TestSqliteVec:
    def test_vec_enabled(self, db):
        # sqlite-vec should load in test env
        assert db.vec_enabled is True

    def test_insert_and_search_vec(self, memory, fake_embedder):
        import hashlib
        content = "vector search test content"
        h = hashlib.sha256(content.encode()).hexdigest()
        memory.insert(content, "2026-02-27", "2026-02-27T10:00:00", content_hash=h)

        emb = fake_embedder.embed(content)
        memory.insert_vector(h, emb)

        query_emb = fake_embedder.embed(content)
        results = memory.search_vec(query_emb, limit=5)
        assert len(results) >= 1
        assert results[0]["content_hash"] == h
        assert results[0]["distance"] < 0.01  # same text → near-zero distance

    def test_vec_different_texts(self, memory, fake_embedder):
        import hashlib
        texts = [
            ("Python programming language", "2026-02-27"),
            ("Hôm nay trời đẹp", "2026-02-27"),
            ("machine learning model", "2026-02-27"),
        ]
        for content, date in texts:
            h = hashlib.sha256(content.encode()).hexdigest()
            memory.insert(content, date, f"{date}T10:00:00", content_hash=h)
            memory.insert_vector(h, fake_embedder.embed(content))

        query_emb = fake_embedder.embed("Python programming language")
        results = memory.search_vec(query_emb, limit=3)
        assert len(results) >= 1
        # First result should be the exact match
        assert results[0]["content_hash"] == hashlib.sha256(b"Python programming language").hexdigest()

    def test_insert_vector_no_op_when_vec_disabled(self, db, fake_embedder):
        """Should not raise even when vec_enabled=False (graceful degradation)."""
        db.memory.vec_enabled = False
        db.memory.insert_vector("any_hash", fake_embedder.embed("test"))  # no exception

    def test_search_vec_returns_empty_when_disabled(self, db, fake_embedder):
        db.memory.vec_enabled = False
        results = db.memory.search_vec(fake_embedder.embed("test"), limit=5)
        assert results == []


# ── get_by_hashes ──────────────────────────────────────────────────────────────

class TestGetByHashes:
    def test_single_hash(self, memory):
        h = _insert(memory, "unique text here", mood="happy")
        result = memory.get_by_hashes([h])
        assert h in result
        assert result[h]["text"] == "unique text here"
        assert result[h]["mood"] == "happy"

    def test_multiple_hashes(self, memory):
        h1 = _insert(memory, "text one")
        h2 = _insert(memory, "text two")
        result = memory.get_by_hashes([h1, h2])
        assert len(result) == 2
        assert result[h1]["text"] == "text one"
        assert result[h2]["text"] == "text two"

    def test_empty_list(self, memory):
        assert memory.get_by_hashes([]) == {}

    def test_nonexistent_hash(self, memory):
        result = memory.get_by_hashes(["deadbeef" * 8])
        assert result == {}


# ── timeline ───────────────────────────────────────────────────────────────────

class TestTimeline:
    def test_timeline_returns_all(self, memory):
        _insert(memory, "Jan entry", date="2026-01-15")
        _insert(memory, "Feb entry", date="2026-02-20")
        result = memory.get_timeline(limit=50)
        assert len(result) == 2

    def test_timeline_date_filter(self, memory):
        _insert(memory, "Jan", date="2026-01-15")
        _insert(memory, "Feb", date="2026-02-20")
        _insert(memory, "Mar", date="2026-03-10")
        result = memory.get_timeline(start_date="2026-01-20", end_date="2026-02-28")
        assert len(result) == 1
        assert result[0]["text"] == "Feb"

    def test_get_dates(self, memory):
        _insert(memory, "day 1", date="2026-01-01")
        _insert(memory, "day 2", date="2026-01-02")
        _insert(memory, "day 1 again", date="2026-01-01")
        dates = memory.get_dates()
        assert len(dates) == 2
        assert "2026-01-01" in dates
        assert "2026-01-02" in dates
