"""HTTP-layer tests for /api/connectors — the webhook connector's auth
logic lives in the route handler itself, so it genuinely needs testing at
the HTTP level rather than as a plain function call."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


@pytest.fixture()
def client(db):  # depends on `db` to ensure tables exist before lifespan's init_db()/sync_ontology_nodes() run
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_catalog_endpoint_lists_five_connectors(client):
    resp = client.get("/api/connectors")
    assert resp.status_code == 200
    body = resp.json()
    types = {entry["type"] for entry in body}
    assert types == {"filesystem", "http", "s3", "database", "gcs", "google_drive", "webhook"}
    webhook_entry = next(e for e in body if e["type"] == "webhook")
    assert webhook_entry["direction"] == "push"


def test_test_endpoint_reports_success(client, tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    resp = client.post("/api/connectors/filesystem/test", json={"config": {"root_path": str(tmp_path)}})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "OK"}


def test_test_endpoint_unknown_connector_404s(client):
    resp = client.post("/api/connectors/nope/test", json={"config": {}})
    assert resp.status_code == 404


def test_run_endpoint_ingests_documents(client, tmp_path):
    (tmp_path / "doc.txt").write_text("A short test document for the connector run endpoint.")
    resp = client.post("/api/connectors/filesystem/run", json={"config": {"root_path": str(tmp_path)}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_documents"] == 1
    assert body["job_id"]


def test_run_endpoint_bad_config_returns_400(client, tmp_path):
    resp = client.post("/api/connectors/filesystem/run", json={"config": {"root_path": str(tmp_path / "missing")}})
    assert resp.status_code == 400


def test_webhook_disabled_by_default_returns_404(client, monkeypatch):
    monkeypatch.delenv("WEBHOOK_INGESTION_TOKEN", raising=False)
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/connectors/webhook/ingest",
            files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
            headers={"Authorization": "Bearer whatever"},
        )
        assert resp.status_code == 404
    finally:
        get_settings.cache_clear()


def test_webhook_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_INGESTION_TOKEN", "correct-token")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/connectors/webhook/ingest",
            files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401
    finally:
        get_settings.cache_clear()


def test_webhook_accepts_correct_token(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_INGESTION_TOKEN", "correct-token")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/connectors/webhook/ingest",
            files={"file": ("doc.txt", io.BytesIO(b"A short webhook-pushed test document."), "text/plain")},
            headers={"Authorization": "Bearer correct-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["document_id"]
    finally:
        get_settings.cache_clear()
