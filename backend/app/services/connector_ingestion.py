"""Wires the portable connector catalog (app/connectors/) into KCIP's own
pipeline. Unlike everything in app/connectors/, this file is deliberately
KCIP-specific — it's the one place that imports both the connector
interface and PipelineOrchestrator."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.connectors.base import ConnectorError
from app.connectors.registry import get_connector_registry
from app.models.ingestion_job import IngestionJob
from app.pipeline.factory import get_pipeline_orchestrator


def run_connector(db: Session, connector_type: str, config: dict) -> IngestionJob:
    """Pulls every document the connector finds and runs each through the
    normal ingestion pipeline (detect -> extract -> classify -> ... ->
    ready), exactly as if it had been uploaded through the UI. Returns
    the IngestionJob so progress/results are visible the same way a
    manual batch upload's are (GET /api/ingestion/jobs/{id})."""
    registry = get_connector_registry()
    connector_cls = registry.get(connector_type)
    connector = connector_cls()

    try:
        documents = list(connector.list_documents(config))
    except ConnectorError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize any connector-internal failure
        raise ConnectorError(f"{connector_type} connector failed: {exc}") from exc

    job = IngestionJob(job_type=f"connector:{connector_type}", total_documents=len(documents))
    db.add(job)
    db.commit()

    orchestrator = get_pipeline_orchestrator(db)
    for doc in documents:
        orchestrator.ingest_document(
            filename=doc.filename,
            content=doc.content,
            source_system=doc.source_system,
            source_uri=doc.source_uri,
            ingestion_job=job,
        )

    return job
