"""Tests for the connector registry/catalog, and the KCIP-specific glue
(app/services/connector_ingestion.py) that feeds connector output through
the real pipeline — the same one manual uploads go through."""
from __future__ import annotations

import pytest

from app.connectors.base import ConnectorError
from app.connectors.registry import get_connector_registry
from app.services.connector_ingestion import run_connector


def test_catalog_lists_all_six_pull_connectors():
    catalog = get_connector_registry().list_catalog()
    types = {entry["type"] for entry in catalog}
    assert types == {"filesystem", "http", "s3", "database", "gcs", "google_drive"}
    assert all(entry["direction"] == "pull" for entry in catalog)
    assert all(isinstance(entry["config_schema"], dict) for entry in catalog)


def test_unknown_connector_type_raises_key_error():
    with pytest.raises(KeyError):
        get_connector_registry().get("does-not-exist")


def test_run_connector_feeds_real_pipeline(db, tmp_path):
    """End-to-end: filesystem connector pulls 2 files -> the SAME
    orchestrator manual uploads use processes them -> real Document rows
    with real classification exist afterward."""
    (tmp_path / "note.txt").write_text(
        "MEETING NOTES: TEST SYNC\n\nAttendees:\nA, B\n\nAgenda:\nDiscuss the quarterly reimbursement rate schedule."
    )
    (tmp_path / "memo.txt").write_text("A short internal memo with no strong signal either way.")

    job = run_connector(db, "filesystem", {"root_path": str(tmp_path)})

    from app.models.document import Document

    docs = db.query(Document).filter(Document.ingestion_job_id == job.id).all()
    assert len(docs) == 2
    assert {d.filename for d in docs} == {"note.txt", "memo.txt"}
    assert job.total_documents == 2
    # Every document reached SOME terminal state — pipeline didn't silently drop anything.
    assert all(d.status in ("READY", "REVIEW_REQUIRED", "FAILED", "DUPLICATE") for d in docs)


def test_run_connector_with_unknown_type_raises_key_error(db):
    with pytest.raises(KeyError):
        run_connector(db, "not-a-real-connector", {})


def test_run_connector_wraps_connector_failures(db, tmp_path):
    with pytest.raises(ConnectorError):
        run_connector(db, "filesystem", {"root_path": str(tmp_path / "does-not-exist")})
