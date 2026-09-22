from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class Embedding(Base):
    """Vector representation of a chunk.

    Stored as a portable JSON float array so the same row works whether the
    active backend is SQLite (POC default) or PostgreSQL+pgvector. When
    VECTOR_BACKEND=pgvector, VectorIndexService additionally mirrors this
    into a native `vector` column for ANN search (see
    app/embeddings/vector_index.py and docs/decisions.md ADR on storage).
    """

    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("chunks.id"), unique=True, index=True)

    model_name: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32))  # local_hash|sentence_transformers|openai_compatible
    dimension: Mapped[int] = mapped_column(Integer)
    vector: Mapped[list] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chunk: Mapped["Chunk"] = relationship(back_populates="embedding")
