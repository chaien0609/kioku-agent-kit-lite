"""Shared fixtures for kioku-lite tests.

All tests use FakeEmbedder + isolated temp DB to avoid:
  - downloading the bge-m3 model (~1GB)
  - polluting ~/.kioku-lite/users/real-user data

Convention: KIOKU_LITE_USER_ID="test" is set via monkeypatch where needed.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from kioku_lite.pipeline.db import KiokuDB
from kioku_lite.pipeline.embedder import FakeEmbedder
from kioku_lite.pipeline.graph_store import GraphStore
from kioku_lite.pipeline.memory_store import MemoryStore


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_kioku.db"


@pytest.fixture
def db(tmp_db_path: Path) -> KiokuDB:
    """Isolated KiokuDB with FakeEmbedder dimensions (128-dim)."""
    kdb = KiokuDB(tmp_db_path, embed_dim=128)
    yield kdb
    kdb.close()


@pytest.fixture
def memory(db: KiokuDB) -> MemoryStore:
    return db.memory


@pytest.fixture
def graph(db: KiokuDB) -> GraphStore:
    return db.graph


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder(dimensions=128)


@pytest.fixture
def service(tmp_path: Path, monkeypatch):
    """KiokuLiteService with all paths isolated to tmp_path."""
    from kioku_lite.config import Settings
    from kioku_lite.service import KiokuLiteService

    settings = Settings(
        user_id="test",
        memory_dir=tmp_path / "memory",
        data_dir=tmp_path / "data",
        embed_provider="fake",
        embed_dim=128,
    )
    svc = KiokuLiteService(settings=settings)
    yield svc
    svc.close()
