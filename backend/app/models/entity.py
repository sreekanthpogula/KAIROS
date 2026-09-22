from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class Entity(Base):
    """A synthetic named entity extracted from a document (org, provider,
    department, regulation, date, monetary value, ...). Provider-independent:
    populated by rule/regex extractors in DEMO_MODE, swappable for an
    LLM/NER provider in LLM_MODE without touching callers."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("chunks.id"), nullable=True)

    entity_type: Mapped[str] = mapped_column(String(64), index=True)  # organization|provider|regulation|date|money...
    value: Mapped[str] = mapped_column(String(512))
    normalized_value: Mapped[str] = mapped_column(String(512))
    confidence: Mapped[float] = mapped_column(Float, default=0.85)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped["Document"] = relationship(back_populates="entities")
