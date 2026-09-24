from __future__ import annotations

import json
from typing import Iterator, Optional

from pydantic import BaseModel, Field

from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError

# Google Docs/Sheets/Slides have no raw file bytes of their own — Drive
# only serves them via an export to a concrete format. This is the same
# problem Vertex AI Search's Drive connector solves; we solve it the same
# way, exporting each native Google type to a plain, RAG-friendly format.
_GOOGLE_EXPORT_MIME_MAP: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
}

_DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


class GoogleDriveConfig(BaseModel):
    credentials_json: str = Field(description="Service account key JSON, as a string")
    folder_id: Optional[str] = Field(default=None, description="Only list files inside this Drive folder")
    query: Optional[str] = Field(default=None, description="Raw Drive API 'q' filter — overrides folder_id if set")
    max_files: int = Field(default=100, description="Safety cap on how many files to pull in one run")


class GoogleDriveConnector(BaseConnector):
    """Lists and downloads files from Google Drive. Google-native
    documents (Docs/Sheets/Slides) are exported to a plain format
    automatically since Drive never serves their raw bytes directly."""

    connector_type = "google_drive"
    display_name = "Google Drive"
    description = "Lists and downloads files from Google Drive — Google Docs/Sheets/Slides are exported to a plain format automatically."
    direction = "pull"

    @classmethod
    def config_schema(cls) -> dict:
        return GoogleDriveConfig.model_json_schema()

    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        try:
            cfg = GoogleDriveConfig.model_validate(config)
        except Exception as exc:
            raise ConnectorError(f"Invalid Google Drive connector config: {exc}") from exc

        try:
            info = json.loads(cfg.credentials_json)
        except json.JSONDecodeError as exc:
            raise ConnectorError(f"credentials_json is not valid JSON: {exc}") from exc

        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        try:
            creds = service_account.Credentials.from_service_account_info(info, scopes=[_DRIVE_READONLY_SCOPE])
            service = build("drive", "v3", credentials=creds)

            if cfg.query:
                query = cfg.query
            elif cfg.folder_id:
                query = f"'{cfg.folder_id}' in parents and trashed = false"
            else:
                query = "trashed = false"

            count = 0
            page_token = None
            while count < cfg.max_files:
                response = (
                    service.files()
                    .list(
                        q=query,
                        fields="nextPageToken, files(id, name, mimeType)",
                        pageSize=min(100, cfg.max_files - count),
                        pageToken=page_token,
                    )
                    .execute()
                )
                for file_meta in response.get("files", []):
                    if count >= cfg.max_files:
                        return
                    content, filename = self._download_file(service, file_meta["id"], file_meta["mimeType"], file_meta["name"])
                    yield ConnectorDocument(
                        filename=filename,
                        content=content,
                        source_uri=f"https://drive.google.com/file/d/{file_meta['id']}",
                        source_system="google-drive-connector",
                        metadata={"file_id": file_meta["id"], "mime_type": file_meta["mimeType"]},
                    )
                    count += 1
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as exc:
            raise ConnectorError(f"Google Drive API error: {exc}") from exc

    @staticmethod
    def _download_file(service, file_id: str, mime_type: str, name: str) -> tuple[bytes, str]:
        export_info = _GOOGLE_EXPORT_MIME_MAP.get(mime_type)
        if export_info:
            export_mime, ext = export_info
            content = service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
            if not name.endswith(ext):
                name = f"{name}{ext}"
        else:
            content = service.files().get_media(fileId=file_id).execute()
        return content, name
