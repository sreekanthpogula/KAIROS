"""Connector contract — the ONE file every connector in this package
depends on.

Design intent: this whole `app/connectors/` package has ZERO imports from
the rest of KCIP (no `app.core`, `app.models`, `app.pipeline`, nothing
FastAPI/SQLAlchemy-model-specific). Its only third-party dependencies are
generic, widely-used libraries (httpx, boto3, sqlalchemy-core). That's
deliberate: you can copy this directory into an entirely different
project and wire `ConnectorDocument` output into whatever ingestion
pipeline that project has — nothing here assumes it's talking to KCIP
specifically. KCIP's own glue code that feeds connector output into
PipelineOrchestrator.ingest_document() lives separately, in
app/services/connector_ingestion.py — THAT file is not portable, and
isn't meant to be.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator


class ConnectorError(Exception):
    """Raised for any connector-specific failure (bad config, auth
    failure, source unreachable) — callers catch this one type rather
    than needing to know each connector's underlying exception classes."""


@dataclass
class ConnectorDocument:
    """One document pulled from a source system. This is the entire
    interface boundary — any downstream pipeline just needs these four
    fields, nothing connector-specific leaks past this point."""

    filename: str
    content: bytes
    source_uri: str
    source_system: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    connector_type: str
    display_name: str
    description: str
    direction: str = "pull"  # "pull" (this connector fetches) or "push" (external systems send to us)

    @classmethod
    @abstractmethod
    def config_schema(cls) -> dict:
        """A JSON-schema-shaped dict describing the config this connector
        needs — enough for a UI to render a form or a CLI to prompt for
        fields, without the caller needing to import this connector's
        internal Pydantic model."""

    @abstractmethod
    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        """Yield every document found at the configured source. Config is
        validated against this connector's own schema internally; a bad
        config raises ConnectorError, not a raw validation exception, so
        callers only need to catch one thing."""

    def test_connection(self, config: dict) -> tuple[bool, str]:
        """Best-effort reachability/credentials check without pulling
        full content. Default implementation just tries to get the first
        item; override if a connector has a cheaper way to check (e.g. a
        HEAD request, a bucket-exists call)."""
        try:
            next(iter(self.list_documents(config)), None)
            return True, "OK"
        except ConnectorError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 - surface any failure as a clean tuple, never raise from a health check
            return False, f"{type(exc).__name__}: {exc}"
