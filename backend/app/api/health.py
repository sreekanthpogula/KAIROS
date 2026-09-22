from __future__ import annotations

from fastapi import APIRouter

from app.core import runtime_state
from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "degraded" if runtime_state.startup_error else "ok",
        "startup_error": runtime_state.startup_error,
        "app_name": settings.app_name,
        "demo_mode": settings.demo_mode,
        "llm_mode": settings.effective_llm_mode,
        "embedding_provider": settings.embedding_provider,
        "vector_backend": settings.vector_backend,
        "database": "postgresql" if settings.is_postgres else "sqlite",
    }
