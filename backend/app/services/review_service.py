"""Human-in-the-loop review resolution (spec section 29).

Both approve and correct preserve the original model prediction alongside
whatever the human decided — the point of this workflow is the audit
trail, not just fixing the label.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.classification_result import ClassificationResult
from app.models.document import Document
from app.models.review_task import ReviewTask
from app.ontology.service import OntologyService
from app.pipeline.orchestrator import PipelineOrchestrator


class InvalidOntologyIdError(Exception):
    pass


class ReviewService:
    def __init__(self, ontology: OntologyService, settings: Settings):
        self.ontology = ontology
        self.settings = settings

    def approve(self, db: Session, review: ReviewTask, orchestrator: PipelineOrchestrator, reviewer: str, notes: str | None) -> ReviewTask:
        review.status = "APPROVED"
        review.reviewer = reviewer
        review.notes = notes
        review.resolved_at = datetime.now(timezone.utc)
        db.commit()

        doc = db.query(Document).filter(Document.id == review.document_id).first()
        orchestrator.resume_after_review(doc)
        return review

    def correct(self, db: Session, review: ReviewTask, orchestrator: PipelineOrchestrator, ontology_id: str, reviewer: str, notes: str | None) -> ReviewTask:
        node = self.ontology.resolve_or_none(ontology_id)
        if not node:
            raise InvalidOntologyIdError(f"'{ontology_id}' is not a valid controlled ontology leaf")

        doc = db.query(Document).filter(Document.id == review.document_id).first()

        db.query(ClassificationResult).filter(ClassificationResult.document_id == doc.id).update({"is_current": False})
        domain_node = self.ontology.domain_of(ontology_id)
        corrected = ClassificationResult(
            document_id=doc.id, document_type=self.ontology.document_type_for(ontology_id) or "unknown",
            document_subtype=self.ontology.document_subtype_for(ontology_id), domain=domain_node.id if domain_node else "unknown",
            ontology_id=ontology_id, confidence=1.0, confidence_action="AUTO_ACCEPT", method="human",
            reasoning_signals=[f"Human correction by {reviewer}" + (f": {notes}" if notes else "")],
            raw_scores={"human_override": True}, classifier_version=self.settings.classifier_version,
            ontology_version=self.ontology.version, is_current=True,
        )
        db.add(corrected)

        doc.document_type = corrected.document_type
        doc.document_subtype = corrected.document_subtype
        doc.domain = corrected.domain
        doc.ontology_id = ontology_id
        doc.ontology_path = self.ontology.path_for(ontology_id)
        doc.classification_confidence = 1.0
        doc.confidence_action = "AUTO_ACCEPT"
        level, groups = self.ontology.security_defaults_for(ontology_id)
        doc.security_level = level
        doc.allowed_groups = groups
        db.commit()

        review.status = "CORRECTED"
        review.reviewer = reviewer
        review.notes = notes
        review.human_correction = {"ontology_id": ontology_id, "document_type": corrected.document_type, "domain": corrected.domain}
        review.resolved_at = datetime.now(timezone.utc)
        db.commit()

        orchestrator.resume_after_review(doc)
        return review


def get_review_service(ontology: OntologyService, settings: Settings) -> ReviewService:
    return ReviewService(ontology, settings)
