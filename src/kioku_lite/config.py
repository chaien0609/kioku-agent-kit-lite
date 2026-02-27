"""Kioku Lite — configuration (zero Docker, SQLite-everything)."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Priority (highest first):
      1. KIOKU_LITE_* environment variables
      2. ~/.kioku-lite/.active_user  (active profile, set via `kioku-lite users --use`)
      3. Defaults in this class

    No config file — everything is either env vars or managed via CLI commands.
    """

    # Embedding provider: "fastembed" | "ollama" | "fake"
    embed_provider: str = "fastembed"
    embed_model: str = "intfloat/multilingual-e5-large"
    embed_dim: int = 1024

    # Ollama (only used when embed_provider="ollama")
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "bge-m3"

    # Paths — derived in model_post_init, override only for advanced use
    memory_dir: Path | None = None
    data_dir: Path | None = None

    model_config = {"env_prefix": "KIOKU_LITE_", "extra": "ignore"}

    def model_post_init(self, __context) -> None:
        """Resolve active user profile and derive storage paths."""
        # Active profile priority:
        #   1. KIOKU_LITE_USER_ID env var (explicit override)
        #   2. ~/.kioku-lite/.active_user (set via `kioku-lite users --use <id>`)
        #   3. Default: "personal"
        user_id = os.environ.get("KIOKU_LITE_USER_ID", "").strip()
        if not user_id:
            active_file = Path.home() / ".kioku-lite" / ".active_user"
            if active_file.exists():
                user_id = active_file.read_text().strip()
        if not user_id:
            user_id = "personal"

        base = os.path.expanduser(f"~/.kioku-lite/users/{user_id}")

        if not self.memory_dir or str(self.memory_dir) in ("", "."):
            object.__setattr__(self, "memory_dir", Path(f"{base}/memory"))
        else:
            object.__setattr__(self, "memory_dir", Path(os.path.expanduser(str(self.memory_dir))))

        if not self.data_dir or str(self.data_dir) in ("", "."):
            object.__setattr__(self, "data_dir", Path(f"{base}/data"))
        else:
            object.__setattr__(self, "data_dir", Path(os.path.expanduser(str(self.data_dir))))

    @property
    def db_path(self) -> Path:
        """Single SQLite file: FTS5 + sqlite-vec vectors + KG graph tables."""
        return Path(str(self.data_dir)) / "kioku.db"

    def ensure_dirs(self) -> None:
        if self.memory_dir:
            Path(str(self.memory_dir)).mkdir(parents=True, exist_ok=True)
        if self.data_dir:
            Path(str(self.data_dir)).mkdir(parents=True, exist_ok=True)


# Singleton
settings = Settings()
