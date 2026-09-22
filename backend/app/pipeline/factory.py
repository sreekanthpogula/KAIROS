from __future__ import annotations

from sqlalchemy.orm import Session

from app.chunkers.selector import get_chunker_selector
from app.classifiers.factory import get_hybrid_classifier
from app.core.config import get_settings
from app.embeddings.service import get_embedding_service
from app.events.bus import get_event_bus
from app.ontology.service import get_ontology_service
from app.pipeline.orchestrator import PipelineOrchestrator
from app.services.entity_extractor import get_entity_extractor
from app.services.file_detector import FileDetector
from app.services.segmenter import DocumentSegmenter


def get_pipeline_orchestrator(db: Session) -> PipelineOrchestrator:
    return PipelineOrchestrator(
        db=db,
        settings=get_settings(),
        file_detector=FileDetector(),
        segmenter=DocumentSegmenter(),
        chunker_selector=get_chunker_selector(),
        classifier=get_hybrid_classifier(),
        entity_extractor=get_entity_extractor(),
        embedding_service=get_embedding_service(),
        ontology=get_ontology_service(),
        event_bus=get_event_bus(),
    )
