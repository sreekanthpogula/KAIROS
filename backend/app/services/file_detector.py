"""Deterministic file-type detection (spec section 10).

Intentionally contains zero ML/LLM logic — mime type and parser routing are
decided from the file extension plus a magic-byte sniff, nothing else. This
keeps the very first pipeline stage cheap, fast, and 100% reproducible,
which matters once you're triaging hundreds of thousands of files (see
docs/scaling.md and the cost-aware routing story in section 63).
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.enums import ParserType

EXTENSION_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".eml": "message/rfc822",
}

EXTENSION_PARSER: dict[str, ParserType] = {
    ".pdf": ParserType.PDF,
    ".docx": ParserType.DOCX,
    ".xlsx": ParserType.XLSX,
    ".pptx": ParserType.PPTX,
    ".html": ParserType.HTML,
    ".htm": ParserType.HTML,
    ".txt": ParserType.TEXT,
    ".md": ParserType.MARKDOWN,
    ".csv": ParserType.CSV,
    ".eml": ParserType.EMAIL,
}

_OOXML_MARKERS: dict[str, str] = {
    "word/document.xml": "docx",
    "xl/workbook.xml": "xlsx",
    "ppt/presentation.xml": "pptx",
}


@dataclass
class FileDetectionResult:
    mime_type: str
    extension: str
    parser_type: str
    is_supported: bool
    integrity_warning: str | None = None


class FileDetector:
    def detect(self, filename: str, content: bytes) -> FileDetectionResult:
        ext = Path(filename).suffix.lower()
        parser_type = EXTENSION_PARSER.get(ext, ParserType.UNKNOWN)
        mime_type = EXTENSION_MIME.get(ext, "application/octet-stream")

        warning = self._integrity_check(ext, content)

        if parser_type == ParserType.UNKNOWN:
            sniffed = self._sniff_ooxml(content)
            if sniffed:
                parser_type = EXTENSION_PARSER[f".{sniffed}"]
                mime_type = EXTENSION_MIME[f".{sniffed}"]
                ext = f".{sniffed}"

        return FileDetectionResult(
            mime_type=mime_type,
            extension=ext,
            parser_type=parser_type.value,
            is_supported=parser_type != ParserType.UNKNOWN,
            integrity_warning=warning,
        )

    @staticmethod
    def _sniff_ooxml(content: bytes) -> str | None:
        if not content.startswith(b"PK\x03\x04"):
            return None
        try:
            with zipfile.ZipFile(BytesIO(content)) as zf:
                names = set(zf.namelist())
                for marker, kind in _OOXML_MARKERS.items():
                    if marker in names:
                        return kind
        except zipfile.BadZipFile:
            return None
        return None

    @staticmethod
    def _integrity_check(ext: str, content: bytes) -> str | None:
        """Cheap magic-byte sanity check so a mismatched/corrupt file fails
        fast at DETECT time with a clear message, rather than deep inside a
        parser stack trace (spec section 42)."""
        if not content:
            return "File is empty (0 bytes)."
        if ext == ".pdf" and not content.startswith(b"%PDF"):
            return "Extension is .pdf but file does not start with a %PDF header."
        if ext in {".docx", ".xlsx", ".pptx"} and not content.startswith(b"PK\x03\x04"):
            return f"Extension is {ext} but file is not a valid OOXML/zip container."
        return None
