"""Tests for the human-in-the-loop review workflow (spec section 29).

Ingests the real "ambiguous_mixed_memo.pdf" sample through the actual
pipeline to get a genuine REVIEW_REQUIRED document + ReviewTask (rather
than hand-constructing one), then exercises ReviewService.approve/correct
against it.
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.enums import IngestionStatus
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.review_task import ReviewTask
from app.ontology.service import get_ontology_service
from app.pipeline.factory import get_pipeline_orchestrator
from app.services.review_service import InvalidOntologyIdError, ReviewService
from tests.conftest import read_sample_bytes

CORRECT_ONTOLOGY_ID = "financial.reimbursement.reimbursement_policy"  # golden label for the ambiguous memo


def _make_review_service() -> ReviewService:
    return ReviewService(get_ontology_service(), get_settings())


def _ingest_ambiguous_doc(db):
    orchestrator = get_pipeline_orchestrator(db)
    doc = orchestrator.ingest_document("ambiguous_mixed_memo.pdf", read_sample_bytes("ambiguous_mixed_memo.pdf"))
    assert doc.status == IngestionStatus.REVIEW_REQUIRED.value, "fixture assumption broke: sample no longer routes to review"
    task = db.query(ReviewTask).filter(ReviewTask.document_id == doc.id).one()
    return doc, task


# --- Controlled ontology enforcement on correction (ties back to section 13)


def test_correct_rejects_an_invented_ontology_id(db):
    doc, task = _ingest_ambiguous_doc(db)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    with pytest.raises(InvalidOntologyIdError):
        service.correct(db, task, orchestrator, ontology_id="made.up.leaf.id", reviewer="alice@example.com", notes=None)


def test_correct_rejects_a_real_but_non_leaf_ontology_id(db):
    # "legal.contracts" is a real category node, not a controlled leaf type
    # -- correction must only ever be allowed to resolve to a leaf.
    doc, task = _ingest_ambiguous_doc(db)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    with pytest.raises(InvalidOntologyIdError):
        service.correct(db, task, orchestrator, ontology_id="legal.contracts", reviewer="alice@example.com", notes=None)


def test_correct_rejection_does_not_change_document_or_task_status(db):
    doc, task = _ingest_ambiguous_doc(db)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    with pytest.raises(InvalidOntologyIdError):
        service.correct(db, task, orchestrator, ontology_id="bogus.id", reviewer="alice@example.com", notes=None)

    refreshed_doc = db.query(Document).filter(Document.id == doc.id).one()
    refreshed_task = db.query(ReviewTask).filter(ReviewTask.id == task.id).one()
    assert refreshed_doc.status == IngestionStatus.REVIEW_REQUIRED.value
    assert refreshed_task.status == "PENDING"


# --- correct(): valid leaf ---------------------------------------------------


def test_correct_with_valid_leaf_moves_document_to_ready(db):
    doc, task = _ingest_ambiguous_doc(db)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    service.correct(db, task, orchestrator, ontology_id=CORRECT_ONTOLOGY_ID, reviewer="alice@example.com", notes="reviewed manually")

    refreshed = db.query(Document).filter(Document.id == doc.id).one()
    assert refreshed.status == IngestionStatus.READY.value
    assert refreshed.ontology_id == CORRECT_ONTOLOGY_ID
    assert refreshed.confidence_action == "AUTO_ACCEPT"
    assert refreshed.classification_confidence == 1.0


def test_correct_preserves_original_prediction_and_records_the_correction(db):
    doc, task = _ingest_ambiguous_doc(db)
    original_prediction_snapshot = dict(task.original_prediction)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    service.correct(db, task, orchestrator, ontology_id=CORRECT_ONTOLOGY_ID, reviewer="alice@example.com", notes="reviewed")

    refreshed_task = db.query(ReviewTask).filter(ReviewTask.id == task.id).one()
    assert refreshed_task.status == "CORRECTED"
    assert refreshed_task.original_prediction == original_prediction_snapshot  # never mutated
    assert refreshed_task.human_correction["ontology_id"] == CORRECT_ONTOLOGY_ID
    assert refreshed_task.reviewer == "alice@example.com"
    assert refreshed_task.notes == "reviewed"
    assert refreshed_task.resolved_at is not None


def test_correct_produces_chunks_and_embeddings_via_resume_after_review(db):
    doc, task = _ingest_ambiguous_doc(db)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    service.correct(db, task, orchestrator, ontology_id=CORRECT_ONTOLOGY_ID, reviewer="alice@example.com", notes=None)

    chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
    embedding_count = (
        db.query(Embedding).join(Chunk, Embedding.chunk_id == Chunk.id).filter(Chunk.document_id == doc.id).count()
    )
    assert chunk_count > 0
    assert embedding_count == chunk_count


# --- approve(): keep the model's own (low-confidence) prediction -----------


def test_approve_moves_document_to_ready_and_resolves_task(db):
    doc, task = _ingest_ambiguous_doc(db)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    service.approve(db, task, orchestrator, reviewer="bob@example.com", notes="looks fine as-is")

    refreshed_doc = db.query(Document).filter(Document.id == doc.id).one()
    refreshed_task = db.query(ReviewTask).filter(ReviewTask.id == task.id).one()
    assert refreshed_doc.status == IngestionStatus.READY.value
    assert refreshed_task.status == "APPROVED"
    assert refreshed_task.reviewer == "bob@example.com"
    assert refreshed_task.resolved_at is not None
    assert refreshed_task.original_prediction is not None  # preserved, never cleared


def test_approve_does_not_touch_original_prediction(db):
    doc, task = _ingest_ambiguous_doc(db)
    original_prediction_snapshot = dict(task.original_prediction)
    service = _make_review_service()
    orchestrator = get_pipeline_orchestrator(db)

    service.approve(db, task, orchestrator, reviewer="bob@example.com", notes=None)

    refreshed_task = db.query(ReviewTask).filter(ReviewTask.id == task.id).one()
    assert refreshed_task.original_prediction == original_prediction_snapshot
