"""Connector catalog. Still zero-dependency on the rest of ECIP — the
registry just knows about connector classes, nothing about how their
output gets used downstream."""
from __future__ import annotations

from app.connectors.base import BaseConnector
from app.connectors.database_connector import DatabaseConnector
from app.connectors.filesystem_connector import FilesystemConnector
from app.connectors.http_connector import HttpConnector
from app.connectors.s3_connector import S3Connector

PULL_CONNECTOR_CLASSES: list[type[BaseConnector]] = [
    FilesystemConnector,
    HttpConnector,
    S3Connector,
    DatabaseConnector,
]


class ConnectorRegistry:
    def __init__(self, connector_classes: list[type[BaseConnector]]):
        self._by_type = {c.connector_type: c for c in connector_classes}

    def list_catalog(self) -> list[dict]:
        return [
            {
                "type": c.connector_type,
                "display_name": c.display_name,
                "description": c.description,
                "direction": c.direction,
                "config_schema": c.config_schema(),
            }
            for c in self._by_type.values()
        ]

    def get(self, connector_type: str) -> type[BaseConnector]:
        if connector_type not in self._by_type:
            raise KeyError(f"Unknown connector type: {connector_type!r}. Known: {sorted(self._by_type)}")
        return self._by_type[connector_type]


_registry = ConnectorRegistry(PULL_CONNECTOR_CLASSES)


def get_connector_registry() -> ConnectorRegistry:
    return _registry
