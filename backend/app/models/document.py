from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)

    # --- File identity (section 8) ---------------------------------------
    filename: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    extension: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    source_system: Mapped[str] = mapped_column(String(128), default="demo-sharepoint")
    source_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1024))

    parser_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # --- Pipeline state (section 9) ---------------------------------------
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)

    # --- Classification / ontology (denormalized "current" view) ----------
    domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    document_subtype: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ontology_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    ontology_path: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    classification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # --- Security (section 28) --------------------------------------------
    security_level: Mapped[str] = mapped_column(String(32), default="internal")
    allowed_groups: Mapped[list] = mapped_column(JSON, default=list)

    # --- Structure summary --------------------------------------------------
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Versioning (section 39) --------------------------------------------
    extractor_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    classifier_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ontology_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    chunker_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    ingestion_job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("ingestion_jobs.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    segments: Mapped[list["DocumentSegment"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    classification_results: Mapped[list["ClassificationResult"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="ClassificationResult.created_at.desc()"
    )
    entities: Mapped[list["Entity"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    review_tasks: Mapped[list["ReviewTask"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    processing_events: Mapped[list["ProcessingEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="ProcessingEvent.created_at"
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(back_populates="documents")
