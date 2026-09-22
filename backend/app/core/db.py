"""Database engine/session wiring.

Storage backend is abstracted behind a single DATABASE_URL: SQLite for a
zero-dependency local demo, PostgreSQL (+pgvector, via docker-compose) for
the production-shaped path. No business logic depends on which one is
active.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        db_path = url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    # Small pool: a serverless function instance (Vercel, etc.) shouldn't
    # hold many connections against a pooled endpoint (e.g. Neon's
    # PgBouncer) — a handful of concurrent instances each opening a large
    # pool exhausts the pooler's own connection limit fast.
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist. POC uses create_all instead of
    migrations; a real deployment would use Alembic revisions instead."""
    from app.models import (  # noqa: F401  (import registers models on Base)
        chunk,
        classification_result,
        document,
        embedding,
        entity,
        ingestion_job,
        ontology_node,
        processing_event,
        retrieval_log,
        review_task,
        segment,
    )

    Base.metadata.create_all(bind=engine)
