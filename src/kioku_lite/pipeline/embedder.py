"""Embedding provider — FastEmbed (ONNX, local, no server required).

FastEmbed supports bge-m3 (1024-dim, multilingual incl. Vietnamese) natively.
Falls back to FakeEmbedder if fastembed is not installed.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Protocol

log = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    dimensions: int

    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    """Local embedding via FastEmbed + ONNX — no server, no Docker.

    Model is downloaded on first use (~1GB for bge-m3) to ~/.cache/fastembed/.
    Subsequent calls use the cached model.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", dimensions: int = 1024):
        self.model_name = model_name
        self.dimensions = dimensions
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from fastembed import TextEmbedding
            log.info("Loading FastEmbed model: %s (first run may download ~1GB)", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        """Embed a single text. Returns a list of floats."""
        results = list(self.model.embed([text]))
        return results[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        results = list(self.model.embed(texts))
        return [r.tolist() for r in results]


class FakeEmbedder:
    """Deterministic fake embedder for testing (zero external dependencies).

    Generates a fixed-dimension vector from text hash.
    Same text always produces the same vector.
    """

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).hexdigest()
        vector = []
        for i in range(self.dimensions):
            idx = i % len(h)
            val = (int(h[idx], 16) - 8) / 8.0  # -1.0 to 0.875
            vector.append(val)
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def make_embedder(provider: str = "fastembed", model: str = "BAAI/bge-m3", dim: int = 1024) -> EmbeddingProvider:
    """Factory — returns the appropriate embedder based on provider config."""
    if provider == "fake":
        return FakeEmbedder(dimensions=dim)

    try:
        embedder = FastEmbedder(model_name=model, dimensions=dim)
        # Warm up / validate
        embedder.embed("test")
        return embedder
    except Exception as e:
        log.warning("FastEmbed unavailable (%s). Falling back to FakeEmbedder.", e)
        return FakeEmbedder(dimensions=dim)
