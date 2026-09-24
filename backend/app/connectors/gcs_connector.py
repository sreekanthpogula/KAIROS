from __future__ import annotations

import json
from typing import Iterator, Optional

from pydantic import BaseModel, Field

from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError


class GcsConfig(BaseModel):
    bucket: str = Field(description="Bucket name")
    prefix: str = Field(default="", description="Only list objects under this prefix")
    project_id: Optional[str] = Field(default=None, description="Omit to use the credential's default project")
    credentials_json: Optional[str] = Field(
        default=None, description="Service account key JSON as a string — omit to use Application Default Credentials"
    )
    max_files: int = Field(default=100, description="Safety cap on how many objects to pull in one run")


class GcsConnector(BaseConnector):
    """Lists and downloads objects from a Google Cloud Storage bucket —
    the GCS equivalent of S3Connector, and the direct parallel to how
    Vertex AI Search's "Data Store" concept treats a Cloud Storage bucket
    as one ingestible source alongside its other pre-built connectors."""

    connector_type = "gcs"
    display_name = "Google Cloud Storage"
    description = "Lists and downloads objects from a Google Cloud Storage bucket."
    direction = "pull"

    @classmethod
    def config_schema(cls) -> dict:
        return GcsConfig.model_json_schema()

    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        try:
            cfg = GcsConfig.model_validate(config)
        except Exception as exc:
            raise ConnectorError(f"Invalid Google Cloud Storage connector config: {exc}") from exc

        from google.api_core.exceptions import GoogleAPIError
        from google.cloud import storage

        try:
            if cfg.credentials_json:
                from google.oauth2 import service_account

                info = json.loads(cfg.credentials_json)
                creds = service_account.Credentials.from_service_account_info(info)
                client = storage.Client(project=cfg.project_id or info.get("project_id"), credentials=creds)
            else:
                client = storage.Client(project=cfg.project_id)

            count = 0
            for blob in client.list_blobs(cfg.bucket, prefix=cfg.prefix):
                if blob.name.endswith("/"):
                    continue
                if count >= cfg.max_files:
                    return
                content = blob.download_as_bytes()
                yield ConnectorDocument(
                    filename=blob.name.rsplit("/", 1)[-1],
                    content=content,
                    source_uri=f"gs://{cfg.bucket}/{blob.name}",
                    source_system="gcs-connector",
                    metadata={"bucket": cfg.bucket, "key": blob.name, "size_bytes": blob.size},
                )
                count += 1
        except json.JSONDecodeError as exc:
            raise ConnectorError(f"credentials_json is not valid JSON: {exc}") from exc
        except GoogleAPIError as exc:
            raise ConnectorError(f"Google Cloud Storage error: {exc}") from exc
