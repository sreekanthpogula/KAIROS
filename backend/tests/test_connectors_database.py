"""Unit tests for app.connectors.database_connector, against a throwaway
SQLite file it never has to know is SQLite specifically — the whole point
of using plain SQLAlchemy-core is that this same connector works
unmodified against Postgres/MySQL/etc. Deliberately NOT the KCIP app
database — this connector reads from *some other system's* table."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.connectors.base import ConnectorError
from app.connectors.database_connector import DatabaseConnector


@pytest.fixture()
def legacy_db(tmp_path: Path) -> str:
    """Simulates a legacy system's attachments table living in its own
    unrelated database."""
    db_path = tmp_path / "legacy_crm.db"
    conn_str = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(conn_str)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE attachments (id INTEGER PRIMARY KEY, file_name TEXT, body TEXT, uploaded_by TEXT)"))
        conn.execute(
            text("INSERT INTO attachments (file_name, body, uploaded_by) VALUES (:fn, :b, :u)"),
            [
                {"fn": "contract.txt", "b": "contract body text", "u": "alice"},
                {"fn": "invoice.txt", "b": "invoice body text", "u": "bob"},
            ],
        )
    engine.dispose()
    return conn_str


def test_pulls_rows_as_documents(legacy_db):
    docs = list(
        DatabaseConnector().list_documents(
            {
                "connection_string": legacy_db,
                "query": "SELECT file_name, body, uploaded_by FROM attachments ORDER BY id",
                "filename_column": "file_name",
                "content_column": "body",
            }
        )
    )

    assert len(docs) == 2
    assert docs[0].filename == "contract.txt"
    assert docs[0].content == b"contract body text"
    assert docs[0].metadata["uploaded_by"] == "alice"
    assert docs[0].source_system == "database-connector"


def test_max_rows_caps_results(legacy_db):
    docs = list(
        DatabaseConnector().list_documents(
            {
                "connection_string": legacy_db,
                "query": "SELECT file_name, body FROM attachments ORDER BY id",
                "filename_column": "file_name",
                "content_column": "body",
                "max_rows": 1,
            }
        )
    )

    assert len(docs) == 1


def test_missing_column_raises_connector_error(legacy_db):
    with pytest.raises(ConnectorError, match="missing configured column"):
        list(
            DatabaseConnector().list_documents(
                {
                    "connection_string": legacy_db,
                    "query": "SELECT file_name FROM attachments",  # no content column selected
                    "filename_column": "file_name",
                    "content_column": "body",
                }
            )
        )


def test_bad_sql_raises_connector_error(legacy_db):
    with pytest.raises(ConnectorError, match="Database query failed"):
        list(
            DatabaseConnector().list_documents(
                {
                    "connection_string": legacy_db,
                    "query": "SELECT * FROM this_table_does_not_exist",
                    "filename_column": "file_name",
                    "content_column": "body",
                }
            )
        )


def test_invalid_config_raises_connector_error():
    with pytest.raises(ConnectorError):
        list(DatabaseConnector().list_documents({}))  # missing required fields


def test_config_schema_describes_required_fields():
    schema = DatabaseConnector.config_schema()
    for field in ("connection_string", "query", "filename_column", "content_column"):
        assert field in schema["properties"]
        assert field in schema.get("required", [])
