from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class ReviewTask(Base):
    """Human-in-the-loop queue entry. Preserves the original model
    prediction alongside any human correction so both remain auditable
    (section 29)."""

    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    classification_result_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("classification_results.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)  # PENDING|APPROVED|CORRECTED|REJECTED
    reason: Mapped[str] = mapped_column(String(256))  # e.g. "confidence 0.54 below review threshold 0.70"

    original_prediction: Mapped[dict] = mapped_column(JSON)
    human_correction: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reviewer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="review_tasks")
