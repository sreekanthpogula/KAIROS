"""Unit tests for app.services.file_detector.FileDetector (spec section 10).

Pure unit tests — no DB, no pipeline. FileDetector is 100% deterministic:
extension -> mime/parser lookup, plus a cheap magic-byte integrity check and
an OOXML zip-sniffing fallback.
"""
from __future__ import annotations

import pytest

from app.core.enums import ParserType
from app.services.file_detector import FileDetector


@pytest.fixture()
def detector() -> FileDetector:
    return FileDetector()


@pytest.mark.parametrize(
    "filename, content, expected_mime, expected_parser",
    [
        ("contract.pdf", b"%PDF-1.7 rest of a pdf", "application/pdf", ParserType.PDF.value),
        (
            "doc.docx",
            b"PK\x03\x04" + b"0" * 20,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ParserType.DOCX.value,
        ),
        (
            "sheet.xlsx",
            b"PK\x03\x04" + b"0" * 20,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ParserType.XLSX.value,
        ),
        (
            "deck.pptx",
            b"PK\x03\x04" + b"0" * 20,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ParserType.PPTX.value,
        ),
        ("page.html", b"<html></html>", "text/html", ParserType.HTML.value),
        ("page.htm", b"<html></html>", "text/html", ParserType.HTML.value),
        ("notes.txt", b"hello world", "text/plain", ParserType.TEXT.value),
        ("readme.md", b"# heading", "text/markdown", ParserType.MARKDOWN.value),
        ("data.csv", b"a,b,c\n1,2,3", "text/csv", ParserType.CSV.value),
        ("message.eml", b"Subject: hi\n\nbody", "message/rfc822", ParserType.EMAIL.value),
    ],
)
def test_detects_mime_and_parser_by_extension(detector, filename, content, expected_mime, expected_parser):
    result = detector.detect(filename, content)
    assert result.mime_type == expected_mime
    assert result.parser_type == expected_parser
    assert result.is_supported is True
    assert result.integrity_warning is None


def test_unsupported_extension_is_marked_unsupported(detector):
    result = detector.detect("archive.xyz", b"some random bytes that are not any known format")
    assert result.parser_type == ParserType.UNKNOWN.value
    assert result.is_supported is False


def test_unsupported_extension_with_no_extension_at_all(detector):
    result = detector.detect("README", b"just plain text, no extension")
    assert result.parser_type == ParserType.UNKNOWN.value
    assert result.is_supported is False


def test_pdf_with_wrong_magic_bytes_gets_integrity_warning(detector):
    result = detector.detect("fake.pdf", b"this is not a pdf at all")
    assert result.parser_type == ParserType.PDF.value  # still routed by extension
    assert result.integrity_warning is not None
    assert "%PDF" in result.integrity_warning


def test_docx_with_wrong_magic_bytes_gets_integrity_warning(detector):
    result = detector.detect("fake.docx", b"this is not a zip container")
    assert result.parser_type == ParserType.DOCX.value
    assert result.integrity_warning is not None
    assert "OOXML" in result.integrity_warning or "zip" in result.integrity_warning


def test_empty_file_gets_integrity_warning(detector):
    result = detector.detect("empty.pdf", b"")
    assert result.integrity_warning is not None
    assert "empty" in result.integrity_warning.lower()


def test_valid_pdf_header_has_no_integrity_warning(detector):
    result = detector.detect("real.pdf", b"%PDF-1.4\n%rest of file")
    assert result.integrity_warning is None


def test_ooxml_sniff_fallback_recovers_docx_from_wrong_extension(detector, tmp_path):
    # Build a minimal real docx-shaped zip (must contain word/document.xml)
    # so the OOXML sniff can identify it despite the wrong/missing extension.
    import zipfile
    from io import BytesIO

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<document/>")
    content = buf.getvalue()

    result = detector.detect("mystery_file.bin", content)
    assert result.parser_type == ParserType.DOCX.value
    assert result.is_supported is True
    assert result.extension == ".docx"


def test_ooxml_sniff_fallback_recovers_xlsx_when_extension_missing(detector):
    import zipfile
    from io import BytesIO

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", "<workbook/>")
    content = buf.getvalue()

    result = detector.detect("no_extension_at_all", content)
    assert result.parser_type == ParserType.XLSX.value
    assert result.is_supported is True


def test_ooxml_sniff_returns_none_for_unrelated_zip(detector):
    # A real zip file, but with none of the recognized OOXML marker paths
    # inside it -> sniff fails, extension-based UNKNOWN routing stands.
    import zipfile
    from io import BytesIO

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("some_random_file.txt", "not office content")
    content = buf.getvalue()

    result = detector.detect("archive.zip", content)
    assert result.parser_type == ParserType.UNKNOWN.value
    assert result.is_supported is False


def test_ooxml_sniff_handles_corrupt_zip_gracefully(detector):
    # Starts with the zip local-file-header magic bytes but isn't actually
    # a valid zip past that -> BadZipFile must be swallowed, not raised.
    result = detector.detect("broken", b"PK\x03\x04" + b"\x00" * 10)
    assert result.parser_type == ParserType.UNKNOWN.value
    assert result.is_supported is False
