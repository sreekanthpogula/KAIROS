from __future__ import annotations

from typing import Iterator, Optional

from pydantic import BaseModel, Field

from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError


class S3Config(BaseModel):
    bucket: str = Field(description="Bucket name")
    prefix: str = Field(default="", description="Only list keys under this prefix")
    endpoint_url: Optional[str] = Field(default=None, description="Set for non-AWS S3-compatible endpoints (MinIO, R2, etc.)")
    region_name: str = Field(default="us-east-1")
    access_key_id: Optional[str] = Field(default=None, description="Omit to use the environment's default AWS credential chain")
    secret_access_key: Optional[str] = Field(default=None)
    max_keys: int = Field(default=100, description="Safety cap on how many objects to pull in one run")


class S3Connector(BaseConnector):
    """Lists and downloads objects from any S3-compatible object store —
    AWS S3, MinIO, Cloudflare R2, Backblaze B2, etc. This is the connector
    shape most enterprise document archives actually use in production
    (see docs/production-scaling.md's Object Storage layer)."""

    connector_type = "s3"
    display_name = "S3-Compatible Object Storage"
    description = "Lists and downloads objects from an S3 bucket (AWS S3, MinIO, R2, or any S3-compatible endpoint)."
    direction = "pull"

    @classmethod
    def config_schema(cls) -> dict:
        return S3Config.model_json_schema()

    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        try:
            cfg = S3Config.model_validate(config)
        except Exception as exc:
            raise ConnectorError(f"Invalid S3 connector config: {exc}") from exc

        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        session_kwargs = {}
        if cfg.access_key_id and cfg.secret_access_key:
            session_kwargs = {"aws_access_key_id": cfg.access_key_id, "aws_secret_access_key": cfg.secret_access_key}

        try:
            client = boto3.client("s3", region_name=cfg.region_name, endpoint_url=cfg.endpoint_url, **session_kwargs)
            paginator = client.get_paginator("list_objects_v2")
            count = 0
            for page in paginator.paginate(Bucket=cfg.bucket, Prefix=cfg.prefix):
                for obj in page.get("Contents", []):
                    if count >= cfg.max_keys:
                        return
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue
                    body = client.get_object(Bucket=cfg.bucket, Key=key)["Body"].read()
                    yield ConnectorDocument(
                        filename=key.rsplit("/", 1)[-1],
                        content=body,
                        source_uri=f"s3://{cfg.bucket}/{key}",
                        source_system="s3-connector",
                        metadata={"bucket": cfg.bucket, "key": key, "size_bytes": obj.get("Size")},
                    )
                    count += 1
        except (BotoCoreError, ClientError) as exc:
            raise ConnectorError(f"S3 error: {exc}") from exc
