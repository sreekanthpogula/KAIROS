from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.embeddings.providers import (
    EmbeddingProvider,
    LocalHashEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)


class EmbeddingService:
    """Batch-first embedding facade (spec section 22). Callers should
    always prefer embed_batch over looping embed_text — the OpenAI-compatible
    provider sends one HTTP call per batch, not per chunk."""

    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    @property
    def model_name(self) -> str:
        return self.provider.name

    @property
    def dimension(self) -> int:
        return self.provider.dimension

    def embed_text(self, text: str) -> list[float]:
        return self.provider.embed_text(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            out.extend(self.provider.embed_batch(texts[i : i + batch_size]))
        return out


def _build_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "sentence_transformers":
        try:
            return SentenceTransformerEmbeddingProvider(settings.embedding_model_name)
        except RuntimeError:
            # Graceful degradation: never let an optional dependency being
            # absent take down the whole pipeline in DEMO_MODE.
            return LocalHashEmbeddingProvider(settings.embedding_dim)
    if settings.embedding_provider == "openai_compatible" and settings.effective_llm_mode:
        return OpenAICompatibleEmbeddingProvider(
            api_base=settings.llm_api_base, api_key=settings.llm_api_key, model=settings.embedding_model_name
        )
    return LocalHashEmbeddingProvider(settings.embedding_dim)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(_build_provider(get_settings()))
