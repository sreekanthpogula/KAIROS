"""Unit tests for app.connectors.gcs_connector, with google.cloud.storage
mocked at the source module (no moto-equivalent exists for GCS the way it
does for S3, and no real GCP project/credentials are available here)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.connectors.base import ConnectorError
from app.connectors.gcs_connector import GcsConnector


def _fake_blob(name: str, content: bytes):
    blob = MagicMock()
    blob.name = name
    blob.size = len(content)
    blob.download_as_bytes.return_value = content
    return blob


@patch("google.cloud.storage.Client")
def test_lists_and_downloads_objects(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.list_blobs.return_value = [_fake_blob("docs/a.txt", b"first"), _fake_blob("docs/b.txt", b"second")]

    docs = list(GcsConnector().list_documents({"bucket": "test-bucket"}))

    assert {d.filename for d in docs} == {"a.txt", "b.txt"}
    assert {d.content for d in docs} == {b"first", b"second"}
    assert all(d.source_uri.startswith("gs://test-bucket/") for d in docs)
    assert all(d.source_system == "gcs-connector" for d in docs)
    mock_client.list_blobs.assert_called_once_with("test-bucket", prefix="")


@patch("google.cloud.storage.Client")
def test_prefix_is_passed_through(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.list_blobs.return_value = []

    list(GcsConnector().list_documents({"bucket": "test-bucket", "prefix": "reports/"}))

    mock_client.list_blobs.assert_called_once_with("test-bucket", prefix="reports/")


@patch("google.cloud.storage.Client")
def test_skips_directory_marker_blobs(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    folder_marker = _fake_blob("docs/", b"")
    real_file = _fake_blob("docs/a.txt", b"content")
    mock_client.list_blobs.return_value = [folder_marker, real_file]

    docs = list(GcsConnector().list_documents({"bucket": "test-bucket"}))

    assert [d.filename for d in docs] == ["a.txt"]


@patch("google.cloud.storage.Client")
def test_max_files_caps_results(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.list_blobs.return_value = [_fake_blob(f"f{i}.txt", b"x") for i in range(5)]

    docs = list(GcsConnector().list_documents({"bucket": "test-bucket", "max_files": 2}))

    assert len(docs) == 2


@patch("google.cloud.storage.Client")
def test_google_api_error_raises_connector_error(mock_client_cls):
    from google.api_core.exceptions import NotFound

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.list_blobs.side_effect = NotFound("bucket does not exist")

    with pytest.raises(ConnectorError, match="Google Cloud Storage error"):
        list(GcsConnector().list_documents({"bucket": "no-such-bucket"}))


def test_invalid_config_raises_connector_error():
    with pytest.raises(ConnectorError):
        list(GcsConnector().list_documents({}))  # missing required bucket


def test_config_schema_describes_required_fields():
    schema = GcsConnector.config_schema()
    assert "bucket" in schema["properties"]
    assert "bucket" in schema.get("required", [])
