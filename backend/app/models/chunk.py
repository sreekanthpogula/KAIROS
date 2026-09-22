from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class Chunk(Base):
    """Retrieval unit. Every chunk denormalizes the classification/ontology/
    security context of its parent document (section 20) so retrieval and
    ACL filtering never need a join to reconstruct the full picture."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    segment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_segments.id"), nullable=True)

    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    chunker_type: Mapped[str] = mapped_column(String(32))  # ContractChunker|TechnicalDocumentChunker|...
    chunker_version: Mapped[str] = mapped_column(String(16))

    section: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Denormalized classification/ontology context -------------------------
    document_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    document_subtype: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    ontology_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    ontology_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    classification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    topics: Mapped[list] = mapped_column(JSON, default=list)
    entities: Mapped[list] = mapped_column(JSON, default=list)

    # Security / lineage -----------------------------------------------------
    security_level: Mapped[str] = mapped_column(String(32), default="internal")
    allowed_groups: Mapped[list] = mapped_column(JSON, default=list)
    source_system: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Versioning ---------------------------------------------------------------
    parser_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    classifier_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ontology_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    segment: Mapped[Optional["DocumentSegment"]] = relationship(back_populates="chunks")
    embedding: Mapped[Optional["Embedding"]] = relationship(back_populates="chunk", uselist=False, cascade="all, delete-orphan")

    def to_metadata_dict(self) -> dict:
        """Exact shape from spec section 20 — used by API responses."""
        return {
            "chunk_id": self.id,
            "document_id": self.document_id,
            "text": self.text,
            "document_type": self.document_type,
            "document_subtype": self.document_subtype,
            "domain": self.domain,
            "ontology_path": self.ontology_path,
            "topics": self.topics or [],
            "entities": self.entities or [],
            "page_start": self.page_start,
            "page_end": self.page_end,
            "section": self.section,
            "classification_confidence": self.classification_confidence,
            "security_level": self.security_level,
            "source_system": self.source_system,
            "source_uri": self.source_uri,
            "parser_version": self.parser_version,
            "classifier_version": self.classifier_version,
            "ontology_version": self.ontology_version,
        }
