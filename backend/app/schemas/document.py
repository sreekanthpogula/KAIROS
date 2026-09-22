from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    mime_type: str
    extension: str
    size_bytes: int
    checksum: str
    source_system: str
    ingestion_status: str
    is_duplicate: bool = False
    duplicate_of_id: Optional[str] = None
    ingestion_job_id: Optional[str] = None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    status: str
    domain: Optional[str] = None
    document_type: Optional[str] = None
    document_subtype: Optional[str] = None
    ontology_id: Optional[str] = None
    classification_confidence: Optional[float] = None
    confidence_action: Optional[str] = None
    security_level: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class DocumentDetail(DocumentSummary):
    original_filename: str
    checksum: str
    source_system: str
    source_uri: Optional[str] = None
    parser_type: Optional[str] = None
    ontology_path: Optional[list[str]] = None
    allowed_groups: list[str] = []
    page_count: Optional[int] = None
    extractor_version: Optional[str] = None
    classifier_version: Optional[str] = None
    ontology_version: Optional[str] = None
    chunker_version: Optional[str] = None
    embedding_model: Optional[str] = None
    ingestion_job_id: Optional[str] = None


class ProcessingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    stage: str
    status: str
    message: Optional[str] = None
    duration_ms: Optional[float] = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int


class DocumentFullDetail(BaseModel):
    """Everything the document detail page needs in one call: metadata,
    classification, ontology, entities, topics, sections, chunk count,
    and processing history."""

    document: DocumentDetail
    classification_history: list[dict]
    entities: list[dict]
    topics: list[str]
    segments: list[dict]
    chunk_count: int
    processing_events: list[ProcessingEventRead]
