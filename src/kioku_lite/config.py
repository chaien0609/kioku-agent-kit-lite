"""Kioku Lite — configuration (zero Docker, SQLite-everything)."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables.

    All storage is in SQLite — no ChromaDB server, no FalkorDB, no Ollama daemon.
    """

    # User context
    user_id: str = "default"

    # Paths (auto-derived if not set)
    memory_dir: Path | None = None
    data_dir: Path | None = None

    # Embedding provider: "fastembed" (default, local ONNX) or "fake" (testing)
    embed_provider: str = "fastembed"
    # Model name — must be supported by fastembed (bge-m3 ✓)
    embed_model: str = "BAAI/bge-m3"
    # Embedding dimensions — bge-m3 produces 1024-dim
    embed_dim: int = 1024

    # LLM for entity extraction (optional — degraded gracefully if missing)
    anthropic_api_key: str = ""

    # User identity hint for entity mapping during search
    # e.g. "Nguyễn Trọng Phúc, also known as phuc-nt, anh"
    user_identity: str = ""

    model_config = {"env_prefix": "KIOKU_LITE_", "env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context) -> None:
        """Derive paths from user_id after loading env."""
        base = f"~/.kioku-lite/users/{self.user_id}" if self.user_id != "default" else "~/.kioku-lite"
        if not self.memory_dir or str(self.memory_dir) in ("", "."):
            object.__setattr__(self, "memory_dir", Path(os.path.expanduser(f"{base}/memory")))
        else:
            object.__setattr__(self, "memory_dir", Path(os.path.expanduser(str(self.memory_dir))))

        if not self.data_dir or str(self.data_dir) in ("", "."):
            object.__setattr__(self, "data_dir", Path(os.path.expanduser(f"{base}/data")))
        else:
            object.__setattr__(self, "data_dir", Path(os.path.expanduser(str(self.data_dir))))

    # ── Derived paths ──────────────────────────────────────────────────────

    @property
    def db_path(self) -> Path:
        """Single SQLite file containing FTS5, vectors (sqlite-vec), and graph tables."""
        return Path(str(self.data_dir)) / "kioku.db"

    def ensure_dirs(self) -> None:
        """Create required directories."""
        if self.memory_dir:
            Path(str(self.memory_dir)).mkdir(parents=True, exist_ok=True)
        if self.data_dir:
            Path(str(self.data_dir)).mkdir(parents=True, exist_ok=True)


# Singleton
settings = Settings()
