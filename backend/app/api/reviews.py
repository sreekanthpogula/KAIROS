from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.document import Document
from app.models.review_task import ReviewTask
from app.ontology.service import get_ontology_service
from app.pipeline.factory import get_pipeline_orchestrator
from app.schemas.review import ReviewApproveRequest, ReviewCorrectRequest, ReviewTaskOut
from app.services.review_service import InvalidOntologyIdError, get_review_service

router = APIRouter()


def _to_out(review: ReviewTask, doc: Document) -> ReviewTaskOut:
    return ReviewTaskOut(
        id=review.id, document_id=review.document_id, document_filename=doc.filename if doc else "unknown",
        status=review.status, reason=review.reason, original_prediction=review.original_prediction,
        human_correction=review.human_correction, reviewer=review.reviewer,
        created_at=review.created_at, resolved_at=review.resolved_at,
    )


@router.get("", response_model=list[ReviewTaskOut])
def list_reviews(status_filter: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ReviewTask)
    if status_filter:
        query = query.filter(ReviewTask.status == status_filter)
    reviews = query.order_by(ReviewTask.created_at.desc()).all()
    doc_map = {d.id: d for d in db.query(Document).filter(Document.id.in_([r.document_id for r in reviews])).all()} if reviews else {}
    return [_to_out(r, doc_map.get(r.document_id)) for r in reviews]


@router.post("/{review_id}/approve", response_model=ReviewTaskOut)
def approve_review(review_id: str, request: ReviewApproveRequest, db: Session = Depends(get_db)):
    review = db.query(ReviewTask).filter(ReviewTask.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review task not found")
    if review.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Review task is already {review.status}")

    service = get_review_service(get_ontology_service(), get_settings())
    orchestrator = get_pipeline_orchestrator(db)
    review = service.approve(db, review, orchestrator, request.reviewer, request.notes)
    doc = db.query(Document).filter(Document.id == review.document_id).first()
    return _to_out(review, doc)


@router.post("/{review_id}/correct", response_model=ReviewTaskOut)
def correct_review(review_id: str, request: ReviewCorrectRequest, db: Session = Depends(get_db)):
    review = db.query(ReviewTask).filter(ReviewTask.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review task not found")
    if review.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Review task is already {review.status}")

    service = get_review_service(get_ontology_service(), get_settings())
    orchestrator = get_pipeline_orchestrator(db)
    try:
        review = service.correct(db, review, orchestrator, request.ontology_id, request.reviewer, request.notes)
    except InvalidOntologyIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    doc = db.query(Document).filter(Document.id == review.document_id).first()
    return _to_out(review, doc)
