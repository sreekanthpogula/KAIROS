from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.retrieval.factory import get_retrieval_service
from app.retrieval.rag import RAGService
from app.services.llm_provider import get_llm_provider


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService(get_retrieval_service(), get_llm_provider(), get_settings())
