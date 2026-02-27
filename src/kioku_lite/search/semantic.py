"""Semantic vector search via sqlite-vec + FastEmbed.

Returns SearchResult with content_hash set (content="" — hydrated by service layer).
"""

from __future__ import annotations

from kioku_lite.pipeline.embedder import EmbeddingProvider
from kioku_lite.pipeline.memory_store import MemoryStore
from kioku_lite.search.bm25 import SearchResult


def vector_search(
    store: MemoryStore,
    embedder: EmbeddingProvider,
    query: str,
    limit: int = 20,
) -> list[SearchResult]:
    """Cosine similarity search using sqlite-vec.

    Returns results with content_hash set, content="" (hydrated upstream by service.py).
    Distance 0=identical → converted to similarity score 1.0.
    """
    if not store.vec_enabled:
        return []

    try:
        embedding = embedder.embed(query)
    except Exception:
        return []

    raw = store.search_vec(embedding, limit=limit)
    if not raw:
        return []

    # Normalize distances: sqlite-vec cosine distance in [0, 2]
    # Convert to similarity: 1 - (distance / 2) to get [0, 1]
    return [
        SearchResult(
            content="",            # hydrated by service layer via content_hash
            date="",
            mood="",
            timestamp="",
            score=max(0.0, 1.0 - r["distance"] / 2),
            source="vector",
            content_hash=r["content_hash"],
        )
        for r in raw
    ]
