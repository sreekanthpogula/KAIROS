"""The pipeline orchestrator — wires every stage from spec section 9's
state machine together:

RECEIVED -> VALIDATED -> EXTRACTING -> EXTRACTED -> CLASSIFYING ->
CLASSIFIED -> ONTOLOGY_MAPPED -> ENRICHED -> [REVIEW_REQUIRED halts here] ->
SEGMENTED -> CHUNKED -> EMBEDDING -> INDEXED -> READY

Each stage is timed and recorded as a ProcessingEvent (the in-process
stand-in for a real event bus — see app/events/bus.py). Stages are
idempotent: re-running the pipeline for a document (retry after failure,
or resume after a human review correction) first clears that document's
previously-derived segments/chunks/embeddings rather than appending to
them, so retries never duplicate data (spec section 38).
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.chunkers.selector import ChunkerSelector
from app.classifiers.base import ClassifierInput
from app.classifiers.hybrid import HybridClassifier
from app.core.config import Settings
from app.core.enums import IngestionStatus, ProcessingEventType
from app.embeddings.service import EmbeddingService
from app.events.bus import EventBus
from app.models.chunk import Chunk
from app.models.classification_result import ClassificationResult
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.entity import Entity
from app.models.ingestion_job import IngestionJob
from app.models.review_task import ReviewTask
from app.models.segment import DocumentSegment
from app.ontology.service import OntologyService
from app.pipeline.exceptions import PipelineStageError
from app.services.entity_extractor import BaseEntityExtractor
from app.services.file_detector import FileDetector
from app.services.segmenter import DocumentSegmenter
from app.services.topic_extractor import extract_topics
from app.extractors.registry import UnsupportedFileTypeError, get_extractor


class PipelineOrchestrator:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        file_detector: FileDetector,
        segmenter: DocumentSegmenter,
        chunker_selector: ChunkerSelector,
        classifier: HybridClassifier,
        entity_extractor: BaseEntityExtractor,
        embedding_service: EmbeddingService,
        ontology: OntologyService,
        event_bus: EventBus,
    ):
        self.db = db
        self.settings = settings
        self.file_detector = file_detector
        self.segmenter = segmenter
        self.chunker_selector = chunker_selector
        self.classifier = classifier
        self.entity_extractor = entity_extractor
        self.embedding_service = embedding_service
        self.ontology = ontology
        self.event_bus = event_bus

    # ------------------------------------------------------------------ #
    # Entry points
    # ------------------------------------------------------------------ #
    def ingest_document(
        self,
        filename: str,
        content: bytes,
        source_system: str = "demo-sharepoint",
        source_uri: str | None = None,
        ingestion_job: IngestionJob | None = None,
    ) -> Document:
        checksum = hashlib.sha256(content).hexdigest()
        existing = self.db.query(Document).filter(Document.checksum == checksum).first()

        detection = self.file_detector.detect(filename, content)

        if existing is not None:
            duplicate = Document(
                filename=filename, original_filename=filename, mime_type=detection.mime_type,
                extension=detection.extension, size_bytes=len(content), checksum=checksum + f"-dup-{existing.id[:8]}",
                source_system=source_system, source_uri=source_uri, storage_path="", parser_type=detection.parser_type,
                status=IngestionStatus.DUPLICATE.value, duplicate_of_id=existing.id,
                ingestion_job_id=ingestion_job.id if ingestion_job else None,
            )
            self.db.add(duplicate)
            self.db.commit()
            self._emit(duplicate, ProcessingEventType.DUPLICATE_DETECTED, "RECEIVED", f"Duplicate of document {existing.id}")
            if ingestion_job:
                ingestion_job.duplicate_documents += 1
                self.db.commit()
            return duplicate

        storage_path = str(Path(self.settings.upload_dir) / f"{hashlib.sha1(checksum.encode()).hexdigest()}{detection.extension}")
        try:
            Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
            Path(storage_path).write_bytes(content)
        except OSError:
            # Read-only deployment filesystem (e.g. Vercel Functions) — the
            # DB-stored `raw_content` below is the real source of truth for
            # retry/resume either way, so this is safe to skip rather than
            # fail the whole upload.
            pass

        doc = Document(
            filename=filename, original_filename=filename, mime_type=detection.mime_type,
            extension=detection.extension, size_bytes=len(content), checksum=checksum,
            source_system=source_system, source_uri=source_uri, storage_path=storage_path,
            raw_content=content, parser_type=detection.parser_type, status=IngestionStatus.RECEIVED.value,
            security_level=self.settings.default_security_level, allowed_groups=["employee"],
            ingestion_job_id=ingestion_job.id if ingestion_job else None,
        )
        self.db.add(doc)
        self.db.commit()
        self._emit(doc, ProcessingEventType.DOCUMENT_UPLOADED, "RECEIVED", f"Received {filename} ({len(content)} bytes)")

        start = time.perf_counter()
        try:
            self._run_pipeline(doc, content, detection.parser_type, detection.integrity_warning)
        except PipelineStageError as exc:
            self._fail(doc, exc.stage, exc.message)
        except Exception as exc:  # pragma: no cover - defensive catch-all
            self._fail(doc, doc.status, f"Unexpected error: {exc}")
        elapsed = time.perf_counter() - start

        if ingestion_job:
            self._update_job_counters(ingestion_job, doc, elapsed)

        return doc

    def retry_document(self, doc: Document) -> Document:
        """Re-runs the pipeline for a document that previously FAILED, or
        resumes one whose classification was just corrected in the Review
        Queue. Always idempotent — see module docstring."""
        content = self._load_original_bytes(doc)
        doc.error_message = None
        try:
            self._run_pipeline(doc, content, doc.parser_type or "unknown", None, resume=True)
        except PipelineStageError as exc:
            self._fail(doc, exc.stage, exc.message)
        except Exception as exc:  # pragma: no cover
            self._fail(doc, doc.status, f"Unexpected error: {exc}")
        return doc

    def resume_after_review(self, doc: Document) -> Document:
        """Called after a human approves/corrects a REVIEW_REQUIRED
        document — continues the pipeline from SEGMENTED onward using the
        (possibly corrected) classification already on the document."""
        content = self._load_original_bytes(doc)
        try:
            extraction = get_extractor(doc.parser_type).extract(content, doc.filename)
            self._clear_derived_rows(doc.id)
            segments = self._stage_segment(doc, extraction, doc.parser_type)
            chunks = self._stage_chunk(doc, segments, extraction)
            self._stage_embed(doc, chunks)
            self._stage_index(doc)
            doc.status = IngestionStatus.READY.value
            self.db.commit()
        except PipelineStageError as exc:
            self._fail(doc, exc.stage, exc.message)
        return doc

    # ------------------------------------------------------------------ #
    # Stages
    # ------------------------------------------------------------------ #
    def _run_pipeline(self, doc: Document, content: bytes, parser_type: str, integrity_warning: str | None, resume: bool = False) -> None:
        self._stage_validate(doc, parser_type, integrity_warning)
        extraction = self._stage_extract(doc, content)
        self._stage_classify(doc, extraction, parser_type)

        if doc.confidence_action == "REVIEW_REQUIRED":
            self._create_review_task(doc)
            doc.status = IngestionStatus.REVIEW_REQUIRED.value
            self.db.commit()
            return

        self._clear_derived_rows(doc.id)
        segments = self._stage_segment(doc, extraction, parser_type)
        chunks = self._stage_chunk(doc, segments, extraction)
        self._stage_embed(doc, chunks)
        self._stage_index(doc)
        doc.status = IngestionStatus.READY.value
        self.db.commit()

    def _stage_validate(self, doc: Document, parser_type: str, integrity_warning: str | None) -> None:
        t0 = time.perf_counter()
        if parser_type == "unknown":
            raise PipelineStageError("VALIDATED", f"Unsupported file type for '{doc.filename}'")
        if integrity_warning:
            raise PipelineStageError("VALIDATED", integrity_warning)
        doc.status = IngestionStatus.VALIDATED.value
        self.db.commit()
        self._emit(doc, ProcessingEventType.VALIDATION_COMPLETED, "VALIDATED", duration=time.perf_counter() - t0)

    def _stage_extract(self, doc: Document, content: bytes):
        t0 = time.perf_counter()
        doc.status = IngestionStatus.EXTRACTING.value
        self.db.commit()
        try:
            extraction = get_extractor(doc.parser_type).extract(content, doc.filename)
        except UnsupportedFileTypeError as exc:
            raise PipelineStageError("EXTRACTING", str(exc)) from exc
        except Exception as exc:
            raise PipelineStageError("EXTRACTING", f"Failed to parse {doc.parser_type} file: {exc}") from exc

        if not extraction.full_text.strip():
            raise PipelineStageError("EXTRACTED", "Document contains no extractable text")

        doc.page_count = extraction.metadata.page_count
        doc.extractor_version = get_extractor(doc.parser_type).version
        doc.status = IngestionStatus.EXTRACTED.value
        self.db.commit()
        self._emit(
            doc, ProcessingEventType.EXTRACTION_COMPLETED, "EXTRACTED",
            f"Extracted {len(extraction.elements)} elements, {extraction.metadata.word_count} words",
            duration=time.perf_counter() - t0,
        )
        return extraction

    def _stage_classify(self, doc: Document, extraction, parser_type: str) -> None:
        t0 = time.perf_counter()
        doc.status = IngestionStatus.CLASSIFYING.value
        self.db.commit()

        headings = [e.text for e in extraction.elements if e.type == "heading"]
        classifier_input = ClassifierInput(
            filename=doc.filename, mime_type=doc.mime_type, parser_type=parser_type,
            full_text=extraction.full_text, headings=headings,
            has_table=any(e.type in ("table", "sheet") for e in extraction.elements),
            has_slide=any(e.type == "slide" for e in extraction.elements),
        )
        output = self.classifier.classify(classifier_input)

        self.db.query(ClassificationResult).filter(ClassificationResult.document_id == doc.id).update({"is_current": False})
        result = ClassificationResult(
            document_id=doc.id, document_type=output.document_type, document_subtype=output.document_subtype,
            domain=output.domain, ontology_id=output.ontology_id, confidence=output.confidence,
            confidence_action=output.confidence_action, method=output.method, reasoning_signals=output.reasoning_signals,
            raw_scores=output.raw_scores, classifier_version=output.classifier_version, ontology_version=output.ontology_version,
            is_current=True,
        )
        self.db.add(result)

        doc.document_type = output.document_type
        doc.document_subtype = output.document_subtype
        doc.domain = output.domain
        doc.ontology_id = output.ontology_id
        doc.ontology_path = self.ontology.path_for(output.ontology_id) if output.ontology_id else None
        doc.classification_confidence = output.confidence
        doc.confidence_action = output.confidence_action
        doc.classifier_version = output.classifier_version
        doc.ontology_version = output.ontology_version
        doc.status = IngestionStatus.CLASSIFIED.value
        self.db.commit()
        self._emit(
            doc, ProcessingEventType.CLASSIFICATION_COMPLETED, "CLASSIFIED",
            f"{output.document_type}/{output.document_subtype} @ {output.confidence:.2f} ({output.confidence_action})",
            duration=time.perf_counter() - t0,
        )

        if output.ontology_id:
            level, groups = self.ontology.security_defaults_for(output.ontology_id)
            doc.security_level = level
            doc.allowed_groups = groups
        doc.status = IngestionStatus.ONTOLOGY_MAPPED.value
        self.db.commit()
        self._emit(doc, ProcessingEventType.ONTOLOGY_MAPPED, "ONTOLOGY_MAPPED", f"Mapped to {doc.ontology_id or 'none'}")

        entities = self.entity_extractor.extract(extraction.full_text)
        for ent in entities:
            self.db.add(
                Entity(document_id=doc.id, entity_type=ent.entity_type, value=ent.value, normalized_value=ent.normalized_value, confidence=ent.confidence)
            )
        doc.status = IngestionStatus.ENRICHED.value
        self.db.commit()
        self._emit(doc, ProcessingEventType.ENRICHMENT_COMPLETED, "ENRICHED", f"Extracted {len(entities)} entities")

    def _create_review_task(self, doc: Document) -> None:
        current = (
            self.db.query(ClassificationResult)
            .filter(ClassificationResult.document_id == doc.id, ClassificationResult.is_current == True)  # noqa: E712
            .first()
        )
        review = ReviewTask(
            document_id=doc.id,
            classification_result_id=current.id if current else None,
            status="PENDING",
            reason=f"confidence {doc.classification_confidence:.2f} below review threshold {self.settings.confidence_secondary_validation:.2f}",
            original_prediction={
                "document_type": doc.document_type, "document_subtype": doc.document_subtype,
                "domain": doc.domain, "ontology_id": doc.ontology_id, "confidence": doc.classification_confidence,
            },
        )
        self.db.add(review)
        self.db.commit()
        self._emit(doc, ProcessingEventType.REVIEW_REQUIRED, "REVIEW_REQUIRED", review.reason)

    def _stage_segment(self, doc: Document, extraction, parser_type: str) -> list:
        t0 = time.perf_counter()
        doc.status = IngestionStatus.SEGMENTED.value
        self.db.commit()
        drafts = self.segmenter.segment(extraction, parser_type)
        for d in drafts:
            self.db.add(
                DocumentSegment(
                    id=d.id, document_id=doc.id, parent_segment_id=d.parent_id, title=d.title,
                    segment_type=d.segment_type, order_index=d.order_index, level=d.level,
                    page_start=d.page_start, page_end=d.page_end, text_preview=d.text[:300],
                )
            )
        self.db.commit()
        self._emit(doc, ProcessingEventType.SEGMENTATION_COMPLETED, "SEGMENTED", f"{len(drafts)} segments", duration=time.perf_counter() - t0)
        return drafts

    def _stage_chunk(self, doc: Document, segments: list, extraction) -> list[Chunk]:
        t0 = time.perf_counter()
        doc.status = IngestionStatus.CHUNKED.value
        self.db.commit()

        chunker = self.chunker_selector.select(doc.parser_type, doc.ontology_id)
        drafts = chunker.chunk(segments)
        doc_entities = self.db.query(Entity).filter(Entity.document_id == doc.id).all()
        ontology_path_str = "/".join(doc.ontology_path) if doc.ontology_path else None

        chunk_rows: list[Chunk] = []
        for idx, d in enumerate(drafts):
            relevant_entities = [e.value for e in doc_entities if e.value.lower() in d.text.lower()]
            chunk_rows.append(
                Chunk(
                    document_id=doc.id, segment_id=d.segment_id, chunk_index=idx, text=d.text,
                    token_count=len(d.text.split()), chunker_type=d.chunker_type, chunker_version=chunker.version,
                    section=d.section_title, page_start=d.page_start, page_end=d.page_end,
                    document_type=doc.document_type, document_subtype=doc.document_subtype, domain=doc.domain,
                    ontology_id=doc.ontology_id, ontology_path=ontology_path_str,
                    classification_confidence=doc.classification_confidence,
                    topics=extract_topics(d.text), entities=relevant_entities,
                    security_level=doc.security_level, allowed_groups=doc.allowed_groups,
                    source_system=doc.source_system, source_uri=doc.source_uri,
                    parser_version=doc.extractor_version, classifier_version=doc.classifier_version,
                    ontology_version=doc.ontology_version,
                )
            )
        self.db.add_all(chunk_rows)
        doc.chunker_version = chunker.version
        self.db.commit()
        self._emit(doc, ProcessingEventType.CHUNKING_COMPLETED, "CHUNKED", f"{len(chunk_rows)} chunks via {chunker.chunker_type}", duration=time.perf_counter() - t0)
        return chunk_rows

    def _stage_embed(self, doc: Document, chunks: list[Chunk]) -> None:
        t0 = time.perf_counter()
        doc.status = IngestionStatus.EMBEDDING.value
        self.db.commit()

        if chunks:
            vectors = self.embedding_service.embed_batch([c.text for c in chunks], batch_size=self.settings.embedding_batch_size)
            for chunk, vector in zip(chunks, vectors):
                self.db.add(
                    Embedding(
                        chunk_id=chunk.id, model_name=self.settings.embedding_model_name if self.embedding_service.model_name != "local_hash" else f"local_hash-{self.embedding_service.dimension}d",
                        provider=self.embedding_service.model_name, dimension=self.embedding_service.dimension, vector=vector,
                    )
                )
        doc.embedding_model = self.embedding_service.model_name
        self.db.commit()
        self._emit(doc, ProcessingEventType.EMBEDDING_COMPLETED, "EMBEDDING", f"Embedded {len(chunks)} chunks with {self.embedding_service.model_name}", duration=time.perf_counter() - t0)

    def _stage_index(self, doc: Document) -> None:
        t0 = time.perf_counter()
        doc.status = IngestionStatus.INDEXED.value
        self.db.commit()
        self._emit(doc, ProcessingEventType.INDEXING_COMPLETED, "INDEXED", "Chunks indexed for retrieval", duration=time.perf_counter() - t0)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_original_bytes(doc: Document) -> bytes:
        """DB-stored bytes are the source of truth (survive serverless cold
        starts); local disk is only a best-effort convenience that may not
        even exist for documents ingested before this column existed."""
        if doc.raw_content is not None:
            return doc.raw_content
        return Path(doc.storage_path).read_bytes()

    def _clear_derived_rows(self, document_id: str) -> None:
        chunk_ids = [c.id for c in self.db.query(Chunk.id).filter(Chunk.document_id == document_id).all()]
        if chunk_ids:
            self.db.query(Embedding).filter(Embedding.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
        self.db.query(Chunk).filter(Chunk.document_id == document_id).delete(synchronize_session=False)
        self.db.query(DocumentSegment).filter(DocumentSegment.document_id == document_id).delete(synchronize_session=False)
        self.db.commit()

    def _fail(self, doc: Document, stage: str, message: str) -> None:
        doc.status = IngestionStatus.FAILED.value
        doc.error_message = f"[{stage}] {message}"
        self.db.commit()
        self._emit(doc, ProcessingEventType.FAILED, stage, message, status="FAILURE")

    def _emit(self, doc: Document, event_type: ProcessingEventType, stage: str, message: str | None = None, status: str = "SUCCESS", duration: float | None = None) -> None:
        from app.models.processing_event import ProcessingEvent

        event = ProcessingEvent(
            document_id=doc.id, event_type=event_type.value, stage=stage, status=status, message=message,
            duration_ms=round(duration * 1000, 2) if duration is not None else None,
        )
        self.db.add(event)
        self.db.commit()
        self.event_bus.publish(event_type.value, {"document_id": doc.id, "stage": stage, "message": message})

    def _update_job_counters(self, job: IngestionJob, doc: Document, elapsed_seconds: float) -> None:
        if doc.status == IngestionStatus.READY.value:
            job.completed_documents += 1
        elif doc.status == IngestionStatus.REVIEW_REQUIRED.value:
            job.review_documents += 1
        elif doc.status == IngestionStatus.FAILED.value:
            job.failed_documents += 1
        processed = job.completed_documents + job.review_documents + job.failed_documents
        prev_total = (job.avg_processing_seconds or 0.0) * (processed - 1)
        job.avg_processing_seconds = (prev_total + elapsed_seconds) / processed if processed else elapsed_seconds
        self.db.commit()
