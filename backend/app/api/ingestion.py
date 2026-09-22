from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.processing_event import ProcessingEvent

router = APIRouter()


def _job_out(job: IngestionJob) -> dict:
    return {
        "id": job.id, "job_type": job.job_type, "status": job.status,
        "total_documents": job.total_documents, "completed_documents": job.completed_documents,
        "review_documents": job.review_documents, "failed_documents": job.failed_documents,
        "duplicate_documents": job.duplicate_documents, "avg_processing_seconds": job.avg_processing_seconds,
        "started_at": job.started_at.isoformat(), "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(IngestionJob).order_by(IngestionJob.started_at.desc()).all()
    return [_job_out(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    documents = db.query(Document).filter(Document.ingestion_job_id == job_id).all()
    events = (
        db.query(ProcessingEvent)
        .filter(ProcessingEvent.document_id.in_([d.id for d in documents]))
        .order_by(ProcessingEvent.created_at)
        .all()
        if documents
        else []
    )

    return {
        **_job_out(job),
        "documents": [
            {"id": d.id, "filename": d.filename, "status": d.status, "confidence": d.classification_confidence, "error_message": d.error_message}
            for d in documents
        ],
        "recent_events": [
            {"document_id": e.document_id, "event_type": e.event_type, "stage": e.stage, "status": e.status, "message": e.message, "duration_ms": e.duration_ms, "created_at": e.created_at.isoformat()}
            for e in events[-50:]
        ],
    }
