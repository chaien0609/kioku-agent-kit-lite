"""Embedding providers for Kioku Lite.

Providers:
  - OllamaEmbedder: calls Ollama HTTP API (same model as kioku-agent-kit full)
  - FastEmbedder:   local ONNX via fastembed (no server required)
  - FakeEmbedder:   deterministic random vectors for testing
"""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.request
from typing import Protocol

log = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    dimensions: int

    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    """Embedding via Ollama HTTP API — same model as kioku-agent-kit.

    Allows kioku-lite to use the exact same embedding model (e.g. multilingual-e5-large)
    as kioku full, for fair benchmark comparisons.

    Requires Ollama running locally (Docker or native).
    Falls back to FakeEmbedder if Ollama is unavailable.

    For E5 models: prepend 'passage:' when indexing, 'query:' when searching.
    Pass prefix="passage: " or prefix="query: " accordingly.
    """

    def __init__(
        self,
        model: str = "jeffh/intfloat-multilingual-e5-large",
        base_url: str = "http://localhost:11434",
        dimensions: int = 1024,
        prefix: str = "",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dimensions = dimensions
        self.prefix = prefix

    def _call(self, text: str) -> list[float]:
        full_text = self.prefix + text
        payload = json.dumps({"model": self.model, "prompt": full_text}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["embedding"]

    def embed(self, text: str) -> list[float]:
        return self._call(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._call(t) for t in texts]


class FastEmbedder:
    """Local embedding via FastEmbed + ONNX — no server, no Docker.

    Model is downloaded on first use to ~/.cache/fastembed/.

    For E5 models: provide prefix='passage: ' (indexing) or 'query: ' (search).
    """

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-large",
        dimensions: int = 1024,
        prefix: str = "",
    ):
        self.model_name = model_name
        self.dimensions = dimensions
        self.prefix = prefix
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from fastembed import TextEmbedding
            log.info("Loading FastEmbed model: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        return list(self.model.embed([self.prefix + text]))[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [r.tolist() for r in self.model.embed([self.prefix + t for t in texts])]


class FakeEmbedder:
    """Deterministic fake embedder for testing (zero external dependencies)."""

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).hexdigest()
        vector = []
        for i in range(self.dimensions):
            idx = i % len(h)
            val = (int(h[idx], 16) - 8) / 8.0
            vector.append(val)
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


# E5 models require passage/query prefix
_E5_MODELS = {"intfloat/multilingual-e5-large", "jeffh/intfloat-multilingual-e5-large"}


def make_embedder(
    provider: str = "fastembed",
    model: str = "intfloat/multilingual-e5-large",
    dim: int = 1024,
    base_url: str = "http://localhost:11434",
    prefix: str = "passage: ",  # default for indexing; use 'query: ' for search
) -> EmbeddingProvider:
    """Factory — returns the appropriate embedder.

    provider: 'fastembed' | 'ollama' | 'fake'
    model:    FastEmbed model name OR Ollama model tag
    prefix:   'passage: ' when indexing, 'query: ' when searching (E5 format)
    """
    if provider == "fake":
        return FakeEmbedder(dimensions=dim)

    if provider == "ollama":
        try:
            e = OllamaEmbedder(model=model, base_url=base_url, dimensions=dim, prefix=prefix)
            e.embed("test")
            log.info("OllamaEmbedder ready: model=%s url=%s prefix=%r", model, base_url, prefix)
            return e
        except Exception as ex:
            log.warning("Ollama unavailable (%s). Falling back to FakeEmbedder.", ex)
            return FakeEmbedder(dimensions=dim)

    # fastembed (default)
    try:
        e = FastEmbedder(model_name=model, dimensions=dim, prefix=prefix)
        e.embed("test")
        return e
    except Exception as ex:
        log.warning("FastEmbed unavailable (%s). Falling back to FakeEmbedder.", ex)
        return FakeEmbedder(dimensions=dim)
