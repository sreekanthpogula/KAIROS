"""Unit tests for app.connectors.s3_connector, against a mocked AWS S3
(moto) — no real AWS account or credentials involved, no network calls."""
from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from app.connectors.base import ConnectorError
from app.connectors.s3_connector import S3Connector


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="ecip-test-bucket")
        client.put_object(Bucket="ecip-test-bucket", Key="docs/a.txt", Body=b"first")
        client.put_object(Bucket="ecip-test-bucket", Key="docs/b.txt", Body=b"second")
        client.put_object(Bucket="ecip-test-bucket", Key="other/c.txt", Body=b"third")
        yield "ecip-test-bucket"


def test_lists_and_downloads_objects(s3_bucket):
    docs = list(S3Connector().list_documents({"bucket": s3_bucket, "region_name": "us-east-1"}))

    by_key = {d.metadata["key"]: d for d in docs}
    assert by_key["docs/a.txt"].content == b"first"
    assert by_key["docs/b.txt"].content == b"second"
    assert by_key["other/c.txt"].content == b"third"
    assert all(d.source_uri.startswith(f"s3://{s3_bucket}/") for d in docs)
    assert all(d.source_system == "s3-connector" for d in docs)


def test_prefix_filters_objects(s3_bucket):
    docs = list(S3Connector().list_documents({"bucket": s3_bucket, "region_name": "us-east-1", "prefix": "docs/"}))

    assert {d.metadata["key"] for d in docs} == {"docs/a.txt", "docs/b.txt"}


def test_max_keys_caps_results(s3_bucket):
    docs = list(S3Connector().list_documents({"bucket": s3_bucket, "region_name": "us-east-1", "max_keys": 1}))

    assert len(docs) == 1


def test_nonexistent_bucket_raises_connector_error(s3_bucket):
    with pytest.raises(ConnectorError):
        list(S3Connector().list_documents({"bucket": "no-such-bucket-exists", "region_name": "us-east-1"}))


def test_invalid_config_raises_connector_error():
    with pytest.raises(ConnectorError):
        list(S3Connector().list_documents({}))  # missing required bucket


def test_config_schema_describes_required_fields():
    schema = S3Connector.config_schema()
    assert "bucket" in schema["properties"]
    assert "bucket" in schema.get("required", [])
