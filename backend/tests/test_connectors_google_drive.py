"""Unit tests for app.connectors.google_drive_connector — the Drive API
client and credentials are mocked at their source modules (no real
Google Workspace/service-account credentials are available here)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.connectors.base import ConnectorError
from app.connectors.google_drive_connector import GoogleDriveConnector

_FAKE_CREDENTIALS_JSON = json.dumps(
    {
        "type": "service_account",
        "project_id": "test-project",
        "private_key": "fake",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
)


def _mock_drive_service(files: list[dict], file_contents: dict[str, bytes]):
    """files: [{"id","name","mimeType"}, ...] as the Drive API would
    return them. file_contents: file_id -> raw bytes .execute() yields
    for either get_media or export_media."""
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": files, "nextPageToken": None}

    def get_media(fileId):
        request = MagicMock()
        request.execute.return_value = file_contents[fileId]
        return request

    def export_media(fileId, mimeType):
        request = MagicMock()
        request.execute.return_value = file_contents[fileId]
        return request

    service.files.return_value.get_media.side_effect = get_media
    service.files.return_value.export_media.side_effect = export_media
    return service


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_lists_and_downloads_regular_files(mock_creds, mock_build):
    mock_creds.return_value = MagicMock()
    files = [{"id": "f1", "name": "contract.pdf", "mimeType": "application/pdf"}]
    mock_build.return_value = _mock_drive_service(files, {"f1": b"%PDF-fake-bytes"})

    docs = list(GoogleDriveConnector().list_documents({"credentials_json": _FAKE_CREDENTIALS_JSON}))

    assert len(docs) == 1
    assert docs[0].filename == "contract.pdf"
    assert docs[0].content == b"%PDF-fake-bytes"
    assert docs[0].source_system == "google-drive-connector"
    assert docs[0].source_uri == "https://drive.google.com/file/d/f1"


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_exports_native_google_doc_to_plain_text(mock_creds, mock_build):
    mock_creds.return_value = MagicMock()
    files = [{"id": "g1", "name": "Meeting Notes", "mimeType": "application/vnd.google-apps.document"}]
    mock_build.return_value = _mock_drive_service(files, {"g1": b"exported plain text body"})

    docs = list(GoogleDriveConnector().list_documents({"credentials_json": _FAKE_CREDENTIALS_JSON}))

    assert docs[0].filename == "Meeting Notes.txt"  # export extension appended
    assert docs[0].content == b"exported plain text body"


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_folder_id_builds_correct_query(mock_creds, mock_build):
    mock_creds.return_value = MagicMock()
    service = _mock_drive_service([], {})
    mock_build.return_value = service

    list(GoogleDriveConnector().list_documents({"credentials_json": _FAKE_CREDENTIALS_JSON, "folder_id": "FOLDER123"}))

    called_q = service.files.return_value.list.call_args.kwargs["q"]
    assert called_q == "'FOLDER123' in parents and trashed = false"


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_explicit_query_overrides_folder_id(mock_creds, mock_build):
    mock_creds.return_value = MagicMock()
    service = _mock_drive_service([], {})
    mock_build.return_value = service

    list(
        GoogleDriveConnector().list_documents(
            {"credentials_json": _FAKE_CREDENTIALS_JSON, "folder_id": "FOLDER123", "query": "name contains 'invoice'"}
        )
    )

    called_q = service.files.return_value.list.call_args.kwargs["q"]
    assert called_q == "name contains 'invoice'"


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_max_files_caps_results(mock_creds, mock_build):
    mock_creds.return_value = MagicMock()
    files = [{"id": f"f{i}", "name": f"doc{i}.txt", "mimeType": "text/plain"} for i in range(5)]
    mock_build.return_value = _mock_drive_service(files, {f"f{i}": b"x" for i in range(5)})

    docs = list(GoogleDriveConnector().list_documents({"credentials_json": _FAKE_CREDENTIALS_JSON, "max_files": 2}))

    assert len(docs) == 2


def test_invalid_credentials_json_raises_connector_error():
    with pytest.raises(ConnectorError, match="not valid JSON"):
        list(GoogleDriveConnector().list_documents({"credentials_json": "not-json{{"}))


def test_invalid_config_raises_connector_error():
    with pytest.raises(ConnectorError):
        list(GoogleDriveConnector().list_documents({}))  # missing required credentials_json


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_http_error_raises_connector_error(mock_creds, mock_build):
    from googleapiclient.errors import HttpError

    mock_creds.return_value = MagicMock()
    fake_resp = MagicMock(status=403)
    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.side_effect = HttpError(fake_resp, b"forbidden")
    mock_build.return_value = mock_service

    with pytest.raises(ConnectorError, match="Google Drive API error"):
        list(GoogleDriveConnector().list_documents({"credentials_json": _FAKE_CREDENTIALS_JSON}))


def test_config_schema_describes_required_fields():
    schema = GoogleDriveConnector.config_schema()
    assert "credentials_json" in schema["properties"]
    assert "credentials_json" in schema.get("required", [])
