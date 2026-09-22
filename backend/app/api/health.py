from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "demo_mode": settings.demo_mode,
        "llm_mode": settings.effective_llm_mode,
        "embedding_provider": settings.embedding_provider,
        "vector_backend": settings.vector_backend,
        "database": "postgresql" if settings.is_postgres else "sqlite",
    }
