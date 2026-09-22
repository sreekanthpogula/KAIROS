from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.enums import IngestionStatus
from app.models.chunk import Chunk
from app.models.classification_result import ClassificationResult
from app.models.document import Document
from app.models.entity import Entity
from app.models.ingestion_job import IngestionJob
from app.models.processing_event import ProcessingEvent
from app.models.segment import DocumentSegment
from app.pipeline.factory import get_pipeline_orchestrator
from app.schemas.document import (
    DocumentDetail,
    DocumentFullDetail,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
    ProcessingEventRead,
)
from app.schemas.lineage import LineageResponse
from app.services.lineage import get_lineage_service

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    file: UploadFile = File(...),
    source_system: str = Form("demo-sharepoint"),
    db: Session = Depends(get_db),
):
    content = file.file.read()
    job = IngestionJob(job_type="single_upload", total_documents=1)
    db.add(job)
    db.commit()

    orchestrator = get_pipeline_orchestrator(db)
    doc = orchestrator.ingest_document(file.filename or "unnamed", content, source_system=source_system, ingestion_job=job)

    return DocumentUploadResponse(
        document_id=doc.id, filename=doc.filename, mime_type=doc.mime_type, extension=doc.extension,
        size_bytes=doc.size_bytes, checksum=doc.checksum.split("-dup-")[0], source_system=doc.source_system,
        ingestion_status=doc.status, is_duplicate=doc.status == IngestionStatus.DUPLICATE.value,
        duplicate_of_id=doc.duplicate_of_id, ingestion_job_id=doc.ingestion_job_id,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: Optional[str] = None,
    domain: Optional[str] = None,
    document_type: Optional[str] = None,
    security_level: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    if domain:
        query = query.filter(Document.domain == domain)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if security_level:
        query = query.filter(Document.security_level == security_level)
    if q:
        query = query.filter(Document.filename.ilike(f"%{q}%"))

    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    return DocumentListResponse(items=[DocumentSummary.model_validate(d) for d in items], total=total)


@router.get("/{document_id}", response_model=DocumentFullDetail)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    classification_history = [
        {
            "id": c.id, "document_type": c.document_type, "document_subtype": c.document_subtype, "domain": c.domain,
            "ontology_id": c.ontology_id, "confidence": c.confidence, "confidence_action": c.confidence_action,
            "method": c.method, "reasoning_signals": c.reasoning_signals, "is_current": c.is_current,
            "created_at": c.created_at.isoformat(),
        }
        for c in db.query(ClassificationResult).filter(ClassificationResult.document_id == document_id).order_by(ClassificationResult.created_at.desc()).all()
    ]
    entities = [
        {"type": e.entity_type, "value": e.value, "normalized_value": e.normalized_value, "confidence": e.confidence}
        for e in db.query(Entity).filter(Entity.document_id == document_id).all()
    ]
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    topics = sorted({t for c in chunks for t in (c.topics or [])})
    segments = [
        {"id": s.id, "title": s.title, "segment_type": s.segment_type, "level": s.level, "parent_segment_id": s.parent_segment_id, "page_start": s.page_start, "page_end": s.page_end}
        for s in db.query(DocumentSegment).filter(DocumentSegment.document_id == document_id).order_by(DocumentSegment.order_index).all()
    ]
    events = (
        db.query(ProcessingEvent)
        .filter(ProcessingEvent.document_id == document_id)
        .order_by(ProcessingEvent.created_at)
        .all()
    )

    return DocumentFullDetail(
        document=DocumentDetail.model_validate(doc),
        classification_history=classification_history,
        entities=entities,
        topics=topics,
        segments=segments,
        chunk_count=len(chunks),
        processing_events=[ProcessingEventRead.model_validate(e) for e in events],
    )


@router.get("/{document_id}/lineage", response_model=LineageResponse)
def get_document_lineage(document_id: str, db: Session = Depends(get_db)):
    result = get_lineage_service().build(db, document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.get("/{document_id}/chunks")
def get_document_chunks(document_id: str, db: Session = Depends(get_db)):
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    return [c.to_metadata_dict() | {"chunk_index": c.chunk_index, "chunker_type": c.chunker_type} for c in chunks]


@router.post("/{document_id}/retry", response_model=DocumentSummary)
def retry_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != IngestionStatus.FAILED.value:
        raise HTTPException(status_code=400, detail=f"Document is in status {doc.status}, not FAILED — nothing to retry")

    orchestrator = get_pipeline_orchestrator(db)
    doc = orchestrator.retry_document(doc)
    return DocumentSummary.model_validate(doc)
