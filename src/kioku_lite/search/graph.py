"""Knowledge graph search via BFS traversal on GraphStore."""

from __future__ import annotations

import re

from kioku_lite.pipeline.graph_store import GraphStore
from kioku_lite.search.bm25 import SearchResult

_STOPWORDS = {
    "là", "và", "của", "có", "cho", "với", "được", "này", "đó", "các",
    "một", "những", "trong", "để", "từ", "theo", "về", "hay", "hoặc",
    "nhưng", "mà", "nếu", "khi", "thì", "đã", "sẽ", "đang", "rồi",
    "nào", "gì", "thế", "sao", "tại", "vì", "bị", "do", "qua", "lại",
    "như", "hơn", "nhất", "rất", "quá", "cũng", "vẫn", "còn", "chỉ",
    "tôi", "anh", "em", "bạn", "mình", "chúng", "họ", "ai",
    "the", "is", "are", "was", "were", "what", "who", "how", "why",
}


def graph_search(
    store: GraphStore,
    query: str,
    limit: int = 20,
    entities: list[str] | None = None,
) -> list[SearchResult]:
    """Search the knowledge graph by entity traversal.

    If `entities` provided (agent pre-extracted): use them as seeds.
    Otherwise: tokenize query and search per meaningful token.
    """
    seed_map: dict[str, object] = {}

    if entities:
        for entity_name in entities:
            pat = r"(?<!\w)" + re.escape(entity_name) + r"(?!\w)"
            for node in store.search_nodes(entity_name, limit=5):
                if re.search(pat, node.name, re.IGNORECASE):
                    seed_map.setdefault(node.name, node)
    else:
        tokens = re.findall(r"\w+", query.lower())
        meaningful = [t for t in tokens if t not in _STOPWORDS and len(t) >= 2]
        if not meaningful:
            return []
        for token in meaningful:
            pat = r"(?<!\w)" + re.escape(token) + r"(?!\w)"
            for node in store.search_nodes(token, limit=5):
                if re.search(pat, node.name, re.IGNORECASE):
                    seed_map.setdefault(node.name, node)

    if not seed_map:
        return []

    ranked_seeds = sorted(
        seed_map.values(),
        key=lambda e: getattr(e, "mention_count", 0),
        reverse=True,
    )[:5]

    seen_hashes: set[str] = set()
    results: list[SearchResult] = []

    for entity in ranked_seeds:
        traversal = store.traverse(entity.name, max_hops=2, limit=limit)
        for edge in traversal.edges:
            key = edge.source_hash or edge.evidence
            if key and key not in seen_hashes:
                seen_hashes.add(key)
                results.append(SearchResult(
                    content=edge.evidence or "",
                    date="", mood="", timestamp="",
                    score=edge.weight,
                    source="graph",
                    content_hash=edge.source_hash,
                ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
