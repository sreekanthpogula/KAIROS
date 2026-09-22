"""Unit tests for app.connectors.filesystem_connector — no DB needed."""
from __future__ import annotations

import pytest

from app.connectors.base import ConnectorError
from app.connectors.filesystem_connector import FilesystemConnector


def test_lists_and_reads_every_file(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("nested")

    docs = list(FilesystemConnector().list_documents({"root_path": str(tmp_path), "glob_pattern": "**/*"}))

    assert {d.filename for d in docs} == {"a.txt", "b.txt", "c.txt"}
    assert {d.content for d in docs} == {b"hello", b"world", b"nested"}
    assert all(d.source_system == "filesystem-connector" for d in docs)
    assert all(d.source_uri.startswith("file://") for d in docs)


def test_glob_pattern_filters_by_extension(tmp_path):
    (tmp_path / "keep.pdf").write_bytes(b"%PDF-fake")
    (tmp_path / "skip.txt").write_text("not a pdf")

    docs = list(FilesystemConnector().list_documents({"root_path": str(tmp_path), "glob_pattern": "*.pdf"}))

    assert [d.filename for d in docs] == ["keep.pdf"]


def test_max_files_caps_results(tmp_path):
    for i in range(5):
        (tmp_path / f"file{i}.txt").write_text(str(i))

    docs = list(FilesystemConnector().list_documents({"root_path": str(tmp_path), "max_files": 2}))

    assert len(docs) == 2


def test_nonexistent_root_raises_connector_error(tmp_path):
    with pytest.raises(ConnectorError, match="does not exist"):
        list(FilesystemConnector().list_documents({"root_path": str(tmp_path / "nope")}))


def test_file_as_root_raises_connector_error(tmp_path):
    f = tmp_path / "notadir.txt"
    f.write_text("x")
    with pytest.raises(ConnectorError, match="not a directory"):
        list(FilesystemConnector().list_documents({"root_path": str(f)}))


def test_invalid_config_raises_connector_error():
    with pytest.raises(ConnectorError):
        list(FilesystemConnector().list_documents({}))  # missing required root_path


def test_config_schema_describes_required_fields():
    schema = FilesystemConnector.config_schema()
    assert "root_path" in schema["properties"]
    assert "root_path" in schema.get("required", [])


def test_test_connection_reports_ok(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    ok, message = FilesystemConnector().test_connection({"root_path": str(tmp_path)})
    assert ok is True
    assert message == "OK"


def test_test_connection_reports_failure(tmp_path):
    ok, message = FilesystemConnector().test_connection({"root_path": str(tmp_path / "missing")})
    assert ok is False
    assert "does not exist" in message
