from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class IngestionJob(Base):
    """Groups one or more documents processed together (a single upload, or
    a batch seed run). Backs the observability 'job details' page
    (section 40)."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_type: Mapped[str] = mapped_column(String(32), default="single_upload")  # single_upload|batch_seed
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")  # RUNNING|COMPLETED|COMPLETED_WITH_ERRORS

    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    completed_documents: Mapped[int] = mapped_column(Integer, default=0)
    review_documents: Mapped[int] = mapped_column(Integer, default=0)
    failed_documents: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_documents: Mapped[int] = mapped_column(Integer, default=0)

    avg_processing_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="ingestion_job")
