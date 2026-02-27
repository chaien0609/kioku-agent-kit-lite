"""Memory store — FTS5 BM25 keyword search + sqlite-vec cosine vector search.

All operations on the `memories` and `memory_vec` tables live here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import struct

from kioku_lite.pipeline.models import FTSResult

log = logging.getLogger(__name__)


class MemoryStore:
    """Handles memory CRUD, FTS5 keyword search, and sqlite-vec vector search.

    Shares a sqlite3.Connection with GraphStore (created by KiokuDB).
    """

    def __init__(self, conn: sqlite3.Connection, embed_dim: int = 1024, vec_enabled: bool = True):
        self.conn = conn
        self.embed_dim = embed_dim
        self.vec_enabled = vec_enabled

    # ── Insert ─────────────────────────────────────────────────────────────────

    def insert(
        self,
        content: str,
        date: str,
        timestamp: str,
        mood: str = "",
        tags: list[str] | None = None,
        content_hash: str = "",
        event_time: str = "",
    ) -> int:
        """Insert a memory. Skips duplicates by content_hash. Returns row id (-1 = dup)."""
        if not content_hash:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO memories (content, date, mood, timestamp, content_hash, tags, event_time) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (content, date, mood, timestamp, content_hash, json.dumps(tags or []), event_time or ""),
            )
            self.conn.commit()
            return cur.lastrowid  # type: ignore
        except sqlite3.IntegrityError:
            return -1

    def insert_vector(self, content_hash: str, embedding: list[float]) -> None:
        """Upsert embedding into the memory_vec table (no-op if vec disabled)."""
        if not self.vec_enabled:
            return
        try:
            blob = struct.pack(f"{len(embedding)}f", *embedding)
            cur = self.conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO memory_vec(content_hash, embedding) VALUES (?, ?)",
                (content_hash, blob),
            )
            self.conn.commit()
        except Exception as e:
            log.warning("Vector insert failed: %s", e)

    # ── Search ─────────────────────────────────────────────────────────────────

    def search_fts(self, query: str, limit: int = 20) -> list[FTSResult]:
        """BM25 keyword search via FTS5. Returns results ordered by relevance.

        Uses term search (each word matched independently) so Vietnamese
        multi-word queries work correctly. Falls back to phrase search if
        the query is a single token.
        """
        # Escape any FTS5 special characters in each token, then join with space
        # This means each word is searched independently (OR-like via BM25 scoring)
        tokens = query.strip().split()
        safe_tokens = ['"' + t.replace('"', '""') + '"' for t in tokens if t]
        safe_query = " ".join(safe_tokens) if safe_tokens else '""'
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT m.id, m.content, m.date, m.mood, m.timestamp, rank, m.content_hash
                FROM memory_fts
                JOIN memories m ON m.id = memory_fts.rowid
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (safe_query, limit),
            )
        except sqlite3.OperationalError:
            return []
        return [
            FTSResult(
                rowid=r[0], content=r[1], date=r[2], mood=r[3],
                timestamp=r[4], rank=abs(r[5]), content_hash=r[6],
            )
            for r in cur.fetchall()
        ]

    def search_vec(self, embedding: list[float], limit: int = 20) -> list[dict]:
        """Cosine similarity search via sqlite-vec.

        Returns list of {content_hash, distance} sorted by distance (lower = closer).
        """
        if not self.vec_enabled:
            return []
        try:
            blob = struct.pack(f"{len(embedding)}f", *embedding)
            cur = self.conn.cursor()
            cur.execute(
                "SELECT content_hash, distance FROM memory_vec WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                (blob, limit),
            )
            return [{"content_hash": r[0], "distance": r[1]} for r in cur.fetchall()]
        except Exception as e:
            log.warning("Vector search failed: %s", e)
            return []

    # ── Lookup ─────────────────────────────────────────────────────────────────

    def get_by_hashes(self, content_hashes: list[str]) -> dict[str, dict]:
        """Bulk lookup by content_hash → {hash: {text, date, mood, ...}}."""
        if not content_hashes:
            return {}
        placeholders = ",".join("?" for _ in content_hashes)
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT content_hash, content, date, mood, timestamp, tags, event_time "
            f"FROM memories WHERE content_hash IN ({placeholders})",
            content_hashes,
        )
        return {
            r[0]: {
                "text": r[1], "date": r[2], "mood": r[3], "timestamp": r[4],
                "tags": json.loads(r[5]) if r[5] else [], "event_time": r[6] or "",
            }
            for r in cur.fetchall()
        }

    def count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memories")
        return cur.fetchone()[0]

    def get_dates(self) -> list[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT date FROM memories ORDER BY date DESC")
        return [r[0] for r in cur.fetchall()]

    def get_timeline(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        sort_by: str = "processing_time",
    ) -> list[dict]:
        """Chronological memory list, optionally filtered by date range."""
        date_col = "event_time" if sort_by == "event_time" else "date"
        order_col = "event_time" if sort_by == "event_time" else "timestamp"
        conditions, params = [], []
        if start_date:
            conditions.append(f"{date_col} >= ?")
            params.append(start_date)
        if end_date:
            conditions.append(f"{date_col} <= ?")
            params.append(end_date)
        if sort_by == "event_time":
            conditions.append("event_time != ''")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT content, date, mood, timestamp, tags, event_time, content_hash FROM memories "
            f"{where} ORDER BY {order_col} DESC LIMIT ?",
            (*params, limit),
        )
        results = [
            {
                "text": r[0], "date": r[1], "mood": r[2], "timestamp": r[3],
                "tags": json.loads(r[4]) if r[4] else [], "event_time": r[5] or "",
                "content_hash": r[6] or "",
            }
            for r in cur.fetchall()
        ]
        results.reverse()
        return results
