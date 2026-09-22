"""Ingests the synthetic demo corpus (data/samples/) through the full ECIP
pipeline: detect -> extract -> classify -> map ontology -> enrich ->
segment -> chunk -> embed -> index.

Run: python scripts/run_demo_ingestion.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.models.ingestion_job import IngestionJob  # noqa: E402
from app.pipeline.factory import get_pipeline_orchestrator  # noqa: E402

SAMPLE_DIR = REPO_ROOT / "data" / "samples"


def main() -> None:
    init_db()
    db = SessionLocal()
    orchestrator = get_pipeline_orchestrator(db)

    files = sorted(
        p for p in SAMPLE_DIR.iterdir() if p.is_file() and p.suffix != ".json" and p.name != ".gitkeep"
    )
    if not files:
        print(f"No sample documents found in {SAMPLE_DIR}. Run scripts/seed_demo_data.py first.")
        return

    job = IngestionJob(job_type="batch_seed", total_documents=len(files))
    db.add(job)
    db.commit()

    print(f"Ingesting {len(files)} documents (job {job.id})...\n")
    t0 = time.perf_counter()

    rows = []
    for f in files:
        doc = orchestrator.ingest_document(f.name, f.read_bytes(), source_system="demo-seed", ingestion_job=job)
        rows.append(doc)
        conf = f"{doc.classification_confidence:.2f}" if doc.classification_confidence is not None else "n/a"
        print(f"  {f.name:45s} -> {doc.status:16s} ontology={doc.ontology_id or '-':45s} conf={conf}")

    elapsed = time.perf_counter() - t0
    db.commit()

    ready = sum(1 for d in rows if d.status == "READY")
    review = sum(1 for d in rows if d.status == "REVIEW_REQUIRED")
    failed = sum(1 for d in rows if d.status == "FAILED")
    duplicate = sum(1 for d in rows if d.status == "DUPLICATE")

    print(f"\nDone in {elapsed:.2f}s - READY={ready} REVIEW_REQUIRED={review} FAILED={failed} DUPLICATE={duplicate}")
    print(f"Job id: {job.id}  (see GET /api/ingestion/jobs/{job.id})")
    db.close()


if __name__ == "__main__":
    main()
