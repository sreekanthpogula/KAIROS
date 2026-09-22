"""Dashboard metrics (spec section 30). Returned as plain dicts rather than
strict Pydantic schemas — this is read-only aggregation/reporting data
consumed directly by frontend charts, where the domain schemas (documents,
chunks, search, rag, review) are where correctness actually matters."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.enums import IngestionStatus
from app.models.chunk import Chunk
from app.models.classification_result import ClassificationResult
from app.models.document import Document
from app.models.embedding import Embedding

router = APIRouter()

_CONFIDENCE_BUCKETS = [("0.0-0.5", 0.0, 0.5), ("0.5-0.7", 0.5, 0.7), ("0.7-0.9", 0.7, 0.9), ("0.9-1.0", 0.9, 1.01)]


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    total = db.query(Document).count()
    by_status = dict(db.query(Document.status, func.count(Document.id)).group_by(Document.status).all())
    ready = by_status.get(IngestionStatus.READY.value, 0)
    failed = by_status.get(IngestionStatus.FAILED.value, 0)
    review = by_status.get(IngestionStatus.REVIEW_REQUIRED.value, 0)
    duplicate = by_status.get(IngestionStatus.DUPLICATE.value, 0)

    avg_confidence = db.query(func.avg(Document.classification_confidence)).filter(Document.classification_confidence.isnot(None)).scalar()
    by_document_type = dict(db.query(Document.document_type, func.count(Document.id)).filter(Document.document_type.isnot(None)).group_by(Document.document_type).all())
    by_domain = dict(db.query(Document.domain, func.count(Document.id)).filter(Document.domain.isnot(None)).group_by(Document.domain).all())
    by_extension = dict(db.query(Document.extension, func.count(Document.id)).group_by(Document.extension).all())

    confidences = [c for (c,) in db.query(Document.classification_confidence).filter(Document.classification_confidence.isnot(None)).all()]
    confidence_distribution = {
        label: sum(1 for c in confidences if lo <= c < hi) for label, lo, hi in _CONFIDENCE_BUCKETS
    }

    current_classifications = db.query(ClassificationResult).filter(ClassificationResult.is_current == True).all()  # noqa: E712
    method_counts = {"rule_or_embedding": 0, "llm_adjudicated": 0, "human_corrected": 0}
    for c in current_classifications:
        if c.method == "human":
            method_counts["human_corrected"] += 1
        elif c.method == "hybrid+llm":
            method_counts["llm_adjudicated"] += 1
        else:
            method_counts["rule_or_embedding"] += 1

    return {
        "documents_ingested": total,
        "processing_success_rate": round(ready / total, 4) if total else 0.0,
        "documents_requiring_review": review,
        "average_classification_confidence": round(avg_confidence, 4) if avg_confidence else 0.0,
        "documents_by_status": by_status,
        "documents_by_type": by_document_type,
        "documents_by_domain": by_domain,
        "documents_by_file_type": by_extension,
        "confidence_distribution": confidence_distribution,
        "chunks_created": db.query(Chunk).count(),
        "embeddings_generated": db.query(Embedding).count(),
        "indexed_documents": ready,
        "duplicate_documents": duplicate,
        "failed_documents": failed,
        "cost_aware_routing": method_counts,
    }
