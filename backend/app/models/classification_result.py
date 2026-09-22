from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class ClassificationResult(Base):
    """One classification attempt. Documents keep the full history so a
    later ontology/classifier version bump never silently overwrites what
    a historical decision actually was (see ADR-005 / docs/decisions.md)."""

    __tablename__ = "classification_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)

    document_type: Mapped[str] = mapped_column(String(128))
    document_subtype: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    domain: Mapped[str] = mapped_column(String(64))
    ontology_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    confidence: Mapped[float] = mapped_column(Float)
    confidence_action: Mapped[str] = mapped_column(String(32))
    method: Mapped[str] = mapped_column(String(16), default="hybrid")  # rule|embedding|llm|hybrid|human

    reasoning_signals: Mapped[list] = mapped_column(JSON, default=list)
    raw_scores: Mapped[dict] = mapped_column(JSON, default=dict)

    classifier_version: Mapped[str] = mapped_column(String(16))
    ontology_version: Mapped[str] = mapped_column(String(16))

    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped["Document"] = relationship(back_populates="classification_results")
