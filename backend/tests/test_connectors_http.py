"""Unit tests for app.connectors.http_connector — served by a real local
HTTP server (no DB needed, no external network access required)."""
from __future__ import annotations

import functools
import http.server
import threading

import pytest

from app.connectors.base import ConnectorError
from app.connectors.http_connector import HttpConnector


@pytest.fixture(scope="module")
def http_server(tmp_path_factory):
    root = tmp_path_factory.mktemp("http_connector_fixture")
    (root / "doc1.txt").write_text("first document")
    (root / "doc2.html").write_text("<html><body>second document</body></html>")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_downloads_multiple_urls(http_server):
    docs = list(HttpConnector().list_documents({"urls": [f"{http_server}/doc1.txt", f"{http_server}/doc2.html"]}))

    by_name = {d.filename: d for d in docs}
    assert by_name["doc1.txt"].content == b"first document"
    assert b"second document" in by_name["doc2.html"].content
    assert all(d.source_system == "http-connector" for d in docs)
    assert all(d.metadata["status_code"] == 200 for d in docs)


def test_404_raises_connector_error(http_server):
    with pytest.raises(ConnectorError, match="Failed to fetch"):
        list(HttpConnector().list_documents({"urls": [f"{http_server}/does-not-exist.txt"]}))


def test_invalid_config_raises_connector_error():
    with pytest.raises(ConnectorError):
        list(HttpConnector().list_documents({}))  # missing required urls


def test_config_schema_describes_required_fields():
    schema = HttpConnector.config_schema()
    assert "urls" in schema["properties"]
    assert "urls" in schema.get("required", [])
