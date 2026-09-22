"""Scale Simulator (spec sections 35, 62, 63).

We deliberately do NOT generate or process 1TB of data locally. Instead we
simulate document counts, throughput, and worker topology, calibrated two
ways:

1. Ratios that describe *this POC's own measured behavior* (chunks per
   document, confidence-band distribution) come from actually querying
   this database — not invented.
2. Everything about a corpus this POC never loads (average file size at
   enterprise scale, worker throughput) is grounded in widely-cited public
   reference points, not benchmarked against a real loaded dataset. See
   REFERENCE_NOTES below and docs/evaluation.md for the full caveat.

Every number this module returns is explicitly labeled SIMULATED in the
response — nothing here should be read as a benchmark result.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.classification_result import ClassificationResult
from app.models.document import Document

REFERENCE_NOTES = {
    "avg_document_size": (
        "2.4 MB/document blends widely-cited enterprise content management "
        "guidance (AIIM/ECM industry surveys): native office documents "
        "typically 0.5-2MB, scanned/OCR'd pages typically 1-3MB, for a "
        "heterogeneous mix. Not measured against a loaded dataset."
    ),
    "clinical_note_volume": (
        "The public MIMIC-III/MIMIC-IV critical-care database (PhysioNet, "
        "Beth Israel Deaconess) documents ~6GB of core structured ICU data "
        "for ~40,000 patients, alongside a much larger free-text clinical "
        "notes companion release — commonly cited evidence that free-text "
        "clinical documentation, not structured records, dominates storage "
        "volume in a healthcare enterprise. Referenced for context only; "
        "this POC's corpus is entirely synthetic."
    ),
    "unstructured_share": (
        "AIIM's long-running industry surveys are commonly cited for the "
        "finding that 80-90% of enterprise content is unstructured "
        "(documents, email, scans) rather than structured database rows — "
        "the core justification for this POC's ingestion architecture."
    ),
    "worker_throughput": (
        "150 documents/worker/hour is an illustrative planning estimate for "
        "a pipeline doing extraction + classification + embedding on "
        "typical office-document-sized files — NOT a benchmark of this "
        "codebase under load."
    ),
}

AVG_DOCUMENT_SIZE_MB = 2.4
AVG_PAGES_PER_DOCUMENT = 8
DOCS_PER_WORKER_PER_HOUR = 150
DEFAULT_WORKER_COUNT = 8

SCALE_PRESETS = [15, 1_000, 10_000, 100_000, "1TB"]


def resolve_document_count(preset: str) -> int:
    """Translates the "1TB" preset into an equivalent document count using
    AVG_DOCUMENT_SIZE_MB, so the caller only ever has to reason about
    document counts. 1TB / 2.4MB ≈ 437,000 documents — an illustrative
    figure, not a claim about any real corpus (see REFERENCE_NOTES)."""
    if preset == "1TB":
        one_tb_mb = 1024 * 1024
        return round(one_tb_mb / AVG_DOCUMENT_SIZE_MB)
    return int(preset)


def _measured_chunks_per_document(db: Session) -> float:
    doc_count = db.query(Document).count()
    chunk_count = db.query(Chunk).count()
    return chunk_count / doc_count if doc_count else 3.4  # fallback: this POC's own typical ratio


def _measured_confidence_bands(db: Session) -> dict[str, float]:
    current = db.query(ClassificationResult).filter(ClassificationResult.is_current == True).all()  # noqa: E712
    total = len(current)
    if not total:
        return {"auto_deterministic": 0.63, "llm_band": 0.15, "human_review": 0.22}

    # Mutually exclusive by confidence_action, so the three percentages
    # sum to 1.0 — llm_band is "would additionally route to an LLM if
    # LLM_MODE were on" (SECONDARY_VALIDATION), not a subset of
    # auto_deterministic (AUTO_ACCEPT only).
    review_required = sum(1 for c in current if c.confidence_action == "REVIEW_REQUIRED")
    llm_band = sum(1 for c in current if c.confidence_action == "SECONDARY_VALIDATION")
    auto_accept = sum(1 for c in current if c.confidence_action == "AUTO_ACCEPT")

    return {
        "auto_deterministic": round(auto_accept / total, 4),
        "llm_band": round(llm_band / total, 4),
        "human_review": round(review_required / total, 4),
    }


def simulate(db: Session, document_count: int, worker_count: int = DEFAULT_WORKER_COUNT) -> dict:
    chunks_per_doc = _measured_chunks_per_document(db)
    bands = _measured_confidence_bands(db)

    total_size_gb = (document_count * AVG_DOCUMENT_SIZE_MB) / 1024
    estimated_chunks = round(document_count * chunks_per_doc)
    estimated_pages = document_count * AVG_PAGES_PER_DOCUMENT

    worker_hours = document_count / DOCS_PER_WORKER_PER_HOUR / max(worker_count, 1)

    return {
        "simulated": True,
        "inputs": {"document_count": document_count, "worker_count": worker_count},
        "storage": {
            "estimated_total_size_gb": round(total_size_gb, 2),
            "estimated_total_size_tb": round(total_size_gb / 1024, 4),
            "avg_document_size_mb": AVG_DOCUMENT_SIZE_MB,
        },
        "volume": {
            "estimated_pages": estimated_pages,
            "estimated_chunks": estimated_chunks,
            "estimated_embeddings": estimated_chunks,
            "chunks_per_document_ratio": round(chunks_per_doc, 2),
            "chunks_per_document_ratio_source": "measured from this POC's own database" if chunks_per_doc != 3.4 else "POC fallback default (no documents ingested yet)",
        },
        "processing": {
            "estimated_processing_hours": round(worker_hours, 2),
            "docs_per_worker_per_hour": DOCS_PER_WORKER_PER_HOUR,
        },
        "cost_aware_routing": {
            "auto_deterministic_pct": bands["auto_deterministic"],
            "llm_adjudicated_pct": bands["llm_band"],
            "human_review_pct": bands["human_review"],
            "source": "measured from this POC's actual classification results" if db.query(ClassificationResult).count() else "POC fallback default (no documents classified yet)",
        },
        "architecture_stages": [
            "Object Storage (S3 / ADLS / GCS)", "Event Bus (Kafka / Event Hub / PubSub)",
            "Ingestion Workers", "Extraction Workers", "Classification Workers",
            "Chunking Workers", "Embedding Workers", "Vector / Search Index",
        ],
        "reference_notes": REFERENCE_NOTES,
    }
