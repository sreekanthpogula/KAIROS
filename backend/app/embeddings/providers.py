"""Embedding provider implementations, all behind the same tiny interface
(embed_text / embed_batch) so EmbeddingService can swap providers without
any caller change (spec section 22).
"""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod

import numpy as np

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "as", "by", "is",
    "are", "be", "this", "that", "shall", "will", "at", "from", "any", "may", "not", "it",
}
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def tokenize(text: str) -> list[str]:
    words = [w for w in _TOKEN_RE.findall(text.lower()) if w not in _STOPWORDS]
    bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return words + bigrams


class EmbeddingProvider(ABC):
    name: str
    dimension: int

    @abstractmethod
    def embed_text(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Dependency-free deterministic embedding via feature hashing
    (Weinberger et al.) over unigrams + bigrams.

    This is NOT a learned semantic embedding — it is a bag-of-hashed-terms
    vector, so it captures lexical/keyword overlap rather than true
    semantic meaning. It is the guaranteed-to-run DEMO_MODE default
    specifically because it needs no model download and no GPU/CPU-heavy
    inference. See docs/decisions.md for the trade-off vs.
    sentence-transformers.
    """

    name = "local_hash"

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        vec = np.zeros(self.dimension, dtype=np.float32)
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Optional, higher-quality local embedding. Requires
    `pip install -r backend/requirements-optional.txt`. Lazily imported so
    the POC never fails to boot because torch isn't installed."""

    name = "sentence_transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Run "
                "`pip install -r backend/requirements-optional.txt` or set "
                "EMBEDDING_PROVIDER=local_hash."
            ) from exc
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """LLM_MODE provider — calls any OpenAI-compatible `/embeddings`
    endpoint. Only used when settings.effective_llm_mode is true."""

    name = "openai_compatible"

    def __init__(self, api_base: str, api_key: str, model: str, dimension: int = 1536):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx

        resp = httpx.post(
            f"{self.api_base}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in data]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]
