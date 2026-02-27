"""Shared SearchResult dataclass + BM25 search via FTS5."""

from __future__ import annotations

from dataclasses import dataclass

from kioku_lite.pipeline.memory_store import MemoryStore


@dataclass
class SearchResult:
    """Unified search result across all three backends."""
    content: str
    date: str
    mood: str
    timestamp: str
    score: float
    source: str          # "bm25" | "vector" | "graph"
    content_hash: str = ""


def bm25_search(store: MemoryStore, query: str, limit: int = 20) -> list[SearchResult]:
    """BM25 keyword search. Scores normalized to 0-1 relative to best match."""
    raw = store.search_fts(query, limit=limit)
    if not raw:
        return []
    max_score = max(r.rank for r in raw) or 1.0
    return [
        SearchResult(
            content=r.content, date=r.date, mood=r.mood, timestamp=r.timestamp,
            score=r.rank / max_score, source="bm25", content_hash=r.content_hash,
        )
        for r in raw
    ]
