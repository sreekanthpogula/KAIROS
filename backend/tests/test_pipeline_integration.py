"""Integration tests for app.pipeline.orchestrator.PipelineOrchestrator.

Exercises the real, fully-wired pipeline (file detection -> extraction ->
classification -> ontology mapping -> entity enrichment -> segmentation ->
chunking -> embedding -> indexing) against a fresh, isolated test database
for each test (see the `db` fixture in conftest.py).
"""
from __future__ import annotations

from app.core.enums import IngestionStatus
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.embedding import Embedding
from app.pipeline.factory import get_pipeline_orchestrator
from tests.conftest import ingest_sample_corpus, read_sample_bytes, sample_corpus_filenames


# --- Duplicate detection (spec section 8 / item 2) --------------------------


def test_duplicate_ingest_marks_second_copy_as_duplicate(db):
    orchestrator = get_pipeline_orchestrator(db)
    content = read_sample_bytes("provider_agreement_northvalley.pdf")

    first = orchestrator.ingest_document("provider_agreement_northvalley.pdf", content)
    assert first.status == IngestionStatus.READY.value

    second = orchestrator.ingest_document("provider_agreement_northvalley.pdf", content)
    assert second.status == IngestionStatus.DUPLICATE.value
    assert second.duplicate_of_id == first.id
    assert second.id != first.id


def test_duplicate_ingest_leaves_original_document_untouched(db):
    orchestrator = get_pipeline_orchestrator(db)
    content = read_sample_bytes("provider_agreement_northvalley.pdf")

    first = orchestrator.ingest_document("provider_agreement_northvalley.pdf", content)
    chunks_before = db.query(Chunk).filter(Chunk.document_id == first.id).count()

    orchestrator.ingest_document("provider_agreement_northvalley.pdf", content)

    refreshed = db.query(Document).filter(Document.id == first.id).one()
    chunks_after = db.query(Chunk).filter(Chunk.document_id == first.id).count()
    assert refreshed.status == IngestionStatus.READY.value
    assert chunks_after == chunks_before  # original was never reprocessed


def test_duplicate_detection_works_across_different_filenames_same_bytes(db):
    # Duplicate detection is checksum-based, not filename-based.
    orchestrator = get_pipeline_orchestrator(db)
    content = read_sample_bytes("provider_agreement_northvalley.pdf")

    first = orchestrator.ingest_document("original_name.pdf", content)
    second = orchestrator.ingest_document("renamed_copy.pdf", content)
    assert second.status == IngestionStatus.DUPLICATE.value
    assert second.duplicate_of_id == first.id


# --- Failure paths (spec section 42 / item 11) ------------------------------


def test_empty_file_fails_with_clear_error_message(db):
    orchestrator = get_pipeline_orchestrator(db)
    doc = orchestrator.ingest_document("empty.txt", b"")
    assert doc.status == IngestionStatus.FAILED.value
    assert doc.error_message is not None
    assert "empty" in doc.error_message.lower()


def test_pdf_extension_with_non_pdf_content_fails_cleanly_at_validated_stage(db):
    orchestrator = get_pipeline_orchestrator(db)
    # No try/except here on purpose: a raw exception leaking out of
    # ingest_document would fail this test just as surely as a wrong status.
    doc = orchestrator.ingest_document("fake.pdf", b"this is definitely not a PDF file")
    assert doc.status == IngestionStatus.FAILED.value
    assert doc.error_message is not None
    assert doc.error_message.startswith("[VALIDATED]")


def test_unsupported_extension_fails_at_validated_stage(db):
    orchestrator = get_pipeline_orchestrator(db)
    doc = orchestrator.ingest_document("notes.xyz", b"whatever content, extension is unsupported")
    assert doc.status == IngestionStatus.FAILED.value
    assert doc.error_message.startswith("[VALIDATED]")
    assert "unsupported" in doc.error_message.lower() or "Unsupported" in doc.error_message


# --- Full corpus integration run (spec item 10) -----------------------------


def test_full_sample_corpus_ingests_to_terminal_states_with_chunks_and_embeddings(db):
    docs = ingest_sample_corpus(db)
    filenames = sample_corpus_filenames()
    assert len(docs) == len(filenames) == 18

    terminal_states = IngestionStatus.terminal_states()
    non_terminal = [(d.filename, d.status) for d in docs if d.status not in {s.value for s in terminal_states}]
    assert non_terminal == [], f"documents left in a non-terminal state: {non_terminal}"

    failed = [(d.filename, d.error_message) for d in docs if d.status == IngestionStatus.FAILED.value]
    assert failed == [], f"unexpected FAILED documents: {failed}"

    chunk_count = db.query(Chunk).count()
    embedding_count = db.query(Embedding).count()
    assert chunk_count > 0
    assert embedding_count > 0
    assert embedding_count == chunk_count

    # The deliberately ambiguous memo is expected to land in human review
    # (see test_classification.py for the full per-document confidence
    # breakdown -- several spreadsheet-shaped documents also legitimately
    # land below the 0.70 review threshold despite guessing the right
    # ontology_id; only the ambiguous memo is asserted on by name here).
    review_docs = [d.filename for d in docs if d.status == IngestionStatus.REVIEW_REQUIRED.value]
    assert "ambiguous_mixed_memo.pdf" in review_docs

    # Every REVIEW_REQUIRED document must have a pending review task with
    # its original (pre-review) prediction preserved.
    from app.models.review_task import ReviewTask

    for doc in docs:
        if doc.status == IngestionStatus.REVIEW_REQUIRED.value:
            task = db.query(ReviewTask).filter(ReviewTask.document_id == doc.id).one()
            assert task.status == "PENDING"
            assert task.original_prediction["ontology_id"] == doc.ontology_id


def test_reingesting_same_bytes_after_full_corpus_run_is_duplicate_not_reprocessed(db):
    docs = ingest_sample_corpus(db)
    chunk_count_before = db.query(Chunk).count()

    target = next(d for d in docs if d.filename == "provider_agreement_northvalley.pdf")
    content = read_sample_bytes("provider_agreement_northvalley.pdf")

    orchestrator = get_pipeline_orchestrator(db)
    repeat = orchestrator.ingest_document("provider_agreement_northvalley.pdf", content)

    assert repeat.status == IngestionStatus.DUPLICATE.value
    assert repeat.duplicate_of_id == target.id
    assert db.query(Chunk).count() == chunk_count_before  # no second processing pass
