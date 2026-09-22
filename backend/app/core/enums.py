"""Shared enumerations. Central so models, schemas, and the pipeline agree."""
from __future__ import annotations

import enum


class IngestionStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    CLASSIFYING = "CLASSIFYING"
    CLASSIFIED = "CLASSIFIED"
    ONTOLOGY_MAPPED = "ONTOLOGY_MAPPED"
    ENRICHED = "ENRICHED"
    SEGMENTED = "SEGMENTED"
    CHUNKED = "CHUNKED"
    EMBEDDING = "EMBEDDING"
    INDEXED = "INDEXED"
    READY = "READY"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DUPLICATE = "DUPLICATE"

    @classmethod
    def terminal_states(cls) -> set["IngestionStatus"]:
        return {cls.READY, cls.FAILED, cls.DUPLICATE, cls.REVIEW_REQUIRED}


# Ordered happy-path pipeline stages, used to render pipeline progress bars
# and to resume idempotently after a failure.
PIPELINE_STAGE_ORDER: list[IngestionStatus] = [
    IngestionStatus.RECEIVED,
    IngestionStatus.VALIDATED,
    IngestionStatus.EXTRACTING,
    IngestionStatus.EXTRACTED,
    IngestionStatus.CLASSIFYING,
    IngestionStatus.CLASSIFIED,
    IngestionStatus.ONTOLOGY_MAPPED,
    IngestionStatus.ENRICHED,
    IngestionStatus.SEGMENTED,
    IngestionStatus.CHUNKED,
    IngestionStatus.EMBEDDING,
    IngestionStatus.INDEXED,
    IngestionStatus.READY,
]


class ConfidenceAction(str, enum.Enum):
    AUTO_ACCEPT = "AUTO_ACCEPT"
    SECONDARY_VALIDATION = "SECONDARY_VALIDATION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ClassificationMethod(str, enum.Enum):
    RULE = "rule"
    EMBEDDING = "embedding"
    LLM = "llm"
    HYBRID = "hybrid"
    HUMAN = "human"


class ReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class SecurityLevel(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


SECURITY_LEVEL_RANK: dict[str, int] = {
    SecurityLevel.PUBLIC: 0,
    SecurityLevel.INTERNAL: 1,
    SecurityLevel.CONFIDENTIAL: 2,
    SecurityLevel.RESTRICTED: 3,
}


class ProcessingEventType(str, enum.Enum):
    DOCUMENT_UPLOADED = "DocumentUploaded"
    VALIDATION_COMPLETED = "ValidationCompleted"
    EXTRACTION_COMPLETED = "ExtractionCompleted"
    CLASSIFICATION_COMPLETED = "ClassificationCompleted"
    ONTOLOGY_MAPPED = "OntologyMapped"
    ENRICHMENT_COMPLETED = "EnrichmentCompleted"
    SEGMENTATION_COMPLETED = "SegmentationCompleted"
    CHUNKING_COMPLETED = "ChunkingCompleted"
    EMBEDDING_COMPLETED = "EmbeddingCompleted"
    INDEXING_COMPLETED = "IndexingCompleted"
    REVIEW_REQUIRED = "ReviewRequired"
    REVIEW_RESOLVED = "ReviewResolved"
    FAILED = "Failed"
    DUPLICATE_DETECTED = "DuplicateDetected"


class DocumentDomain(str, enum.Enum):
    CLINICAL = "clinical"
    ADMINISTRATIVE = "administrative"
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"


class ParserType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"
    TEXT = "text"
    MARKDOWN = "markdown"
    CSV = "csv"
    EMAIL = "email"
    UNKNOWN = "unknown"
