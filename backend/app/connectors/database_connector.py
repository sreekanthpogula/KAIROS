from __future__ import annotations

from typing import Iterator

from pydantic import BaseModel, Field

from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError


class DatabaseConfig(BaseModel):
    connection_string: str = Field(description="Any SQLAlchemy-supported connection string")
    query: str = Field(description="SELECT query returning at least the filename and content columns")
    filename_column: str = Field(description="Name of the column to use as the document's filename")
    content_column: str = Field(description="Name of the column holding the document bytes or text")
    max_rows: int = Field(default=100, description="Safety cap on how many rows to pull in one run")


class DatabaseConnector(BaseConnector):
    """Runs a read-only query against any SQLAlchemy-supported database
    and ingests each row's content column as a document — the common
    shape for legacy systems that store attachments/blobs in a table
    (an old CRM, an ERP attachments table, a ticketing system's DB)."""

    connector_type = "database"
    display_name = "SQL Database"
    description = "Runs a query against any SQL database and ingests each row's content column as a document."
    direction = "pull"

    @classmethod
    def config_schema(cls) -> dict:
        return DatabaseConfig.model_json_schema()

    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        try:
            cfg = DatabaseConfig.model_validate(config)
        except Exception as exc:
            raise ConnectorError(f"Invalid database connector config: {exc}") from exc

        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import SQLAlchemyError

        try:
            engine = create_engine(cfg.connection_string)
        except Exception as exc:
            raise ConnectorError(f"Could not create engine for connection string: {exc}") from exc

        try:
            with engine.connect() as conn:
                result = conn.execute(text(cfg.query))
                count = 0
                for row in result.mappings():
                    if count >= cfg.max_rows:
                        break
                    if cfg.filename_column not in row or cfg.content_column not in row:
                        raise ConnectorError(
                            f"Query result is missing configured column(s): "
                            f"expected '{cfg.filename_column}' and '{cfg.content_column}', got {list(row.keys())}"
                        )
                    filename = str(row[cfg.filename_column])
                    raw = row[cfg.content_column]
                    content = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
                    yield ConnectorDocument(
                        filename=filename,
                        content=content,
                        source_uri=f"db://{engine.url.database or 'default'}/{filename}",
                        source_system="database-connector",
                        metadata={k: v for k, v in row.items() if k not in (cfg.filename_column, cfg.content_column)},
                    )
                    count += 1
        except SQLAlchemyError as exc:
            raise ConnectorError(f"Database query failed: {exc}") from exc
        finally:
            engine.dispose()
