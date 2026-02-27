"""RRF Reranker — identical to kioku-agent-kit."""

from __future__ import annotations

from kioku_lite.search.bm25 import SearchResult


def rrf_rerank(*result_lists: list[SearchResult], k: int = 60, limit: int = 10) -> list[SearchResult]:
    """Reciprocal Rank Fusion across multiple result lists."""
    scores: dict[str, tuple[SearchResult, float]] = {}

    for results in result_lists:
        for rank_pos, result in enumerate(results):
            rrf_score = 1.0 / (k + rank_pos + 1)
            # Dedupe key: prefer content_hash (stable), fall back to content text
            key = result.content_hash or result.content
            if key in scores:
                existing, existing_score = scores[key]
                scores[key] = (existing, existing_score + rrf_score)
            else:
                scores[key] = (result, rrf_score)

    ranked = sorted(scores.values(), key=lambda x: x[1], reverse=True)
    output = []
    for result, score in ranked[:limit]:
        result.score = score
        output.append(result)
    return output
