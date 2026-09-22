"""ECIP Connector Catalog.

Self-contained on purpose — see base.py's module docstring. To reuse this
in another project: copy this directory, keep base.py as-is, and write
your own glue code that calls `connector.list_documents(config)` and
feeds the resulting `ConnectorDocument` objects into your own pipeline.
"""
from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError
from app.connectors.database_connector import DatabaseConnector
from app.connectors.filesystem_connector import FilesystemConnector
from app.connectors.http_connector import HttpConnector
from app.connectors.registry import ConnectorRegistry, get_connector_registry
from app.connectors.s3_connector import S3Connector

__all__ = [
    "BaseConnector",
    "ConnectorDocument",
    "ConnectorError",
    "ConnectorRegistry",
    "get_connector_registry",
    "FilesystemConnector",
    "HttpConnector",
    "S3Connector",
    "DatabaseConnector",
]
