from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class DocumentSegment(Base):
    """A structural/semantic unit within a document (section, slide, sheet,
    table). One document is never assumed to be one semantic unit — see
    docs/chunking.md."""

    __tablename__ = "document_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    parent_segment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_segments.id"), nullable=True
    )

    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    segment_type: Mapped[str] = mapped_column(String(32), default="section")  # section|slide|sheet|table|clause
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)

    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped["Document"] = relationship(back_populates="segments")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="segment")
