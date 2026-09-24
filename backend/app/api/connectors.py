from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.connectors.base import ConnectorError
from app.connectors.registry import get_connector_registry
from app.core.config import get_settings
from app.models.ingestion_job import IngestionJob
from app.pipeline.factory import get_pipeline_orchestrator
from app.schemas.connector import (
    ConnectorCatalogEntry,
    ConnectorRunRequest,
    ConnectorRunResponse,
    ConnectorTestRequest,
    ConnectorTestResponse,
)
from app.services.connector_ingestion import run_connector

router = APIRouter()

_WEBHOOK_CATALOG_ENTRY = {
    "type": "webhook",
    "display_name": "Webhook (inbound push)",
    "description": "Other systems POST documents directly to this endpoint, instead of KCIP pulling from them. "
    "Requires WEBHOOK_INGESTION_TOKEN to be set — see /api/connectors/webhook/ingest.",
    "direction": "push",
    "config_schema": {
        "type": "object",
        "properties": {
            "endpoint": {"type": "string", "const": "POST /api/connectors/webhook/ingest"},
            "auth": {"type": "string", "const": "Authorization: Bearer <WEBHOOK_INGESTION_TOKEN>"},
        },
    },
}


@router.get("", response_model=list[ConnectorCatalogEntry])
def list_connectors():
    catalog = get_connector_registry().list_catalog()
    catalog.append(_WEBHOOK_CATALOG_ENTRY)
    return catalog


@router.post("/{connector_type}/test", response_model=ConnectorTestResponse)
def test_connector(connector_type: str, request: ConnectorTestRequest):
    try:
        connector_cls = get_connector_registry().get(connector_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ok, message = connector_cls().test_connection(request.config)
    return ConnectorTestResponse(ok=ok, message=message)


@router.post("/{connector_type}/run", response_model=ConnectorRunResponse)
def run_connector_endpoint(connector_type: str, request: ConnectorRunRequest, db: Session = Depends(get_db)):
    try:
        job = run_connector(db, connector_type, request.config)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ConnectorRunResponse(
        job_id=job.id, status=job.status, total_documents=job.total_documents,
        completed_documents=job.completed_documents, review_documents=job.review_documents,
        failed_documents=job.failed_documents, duplicate_documents=job.duplicate_documents,
    )


@router.post("/webhook/ingest")
def webhook_ingest(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.webhook_ingestion_token:
        raise HTTPException(status_code=404, detail="Webhook connector is disabled (WEBHOOK_INGESTION_TOKEN not set)")

    expected = f"Bearer {settings.webhook_ingestion_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")

    content = file.file.read()
    job = IngestionJob(job_type="connector:webhook", total_documents=1)
    db.add(job)
    db.commit()

    orchestrator = get_pipeline_orchestrator(db)
    doc = orchestrator.ingest_document(
        filename=file.filename or "webhook_upload",
        content=content,
        source_system="webhook-connector",
        ingestion_job=job,
    )
    return {"document_id": doc.id, "ingestion_status": doc.status}
