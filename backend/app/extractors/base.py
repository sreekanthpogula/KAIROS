"""Extractor interface (spec section 11).

Every format-specific extractor implements the same contract so the
pipeline never branches on file type past the DETECT stage — it just asks
the registry for "whoever can_handle() this parser_type".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel

ElementType = Literal[
    "heading", "paragraph", "table", "table_row", "slide", "sheet", "cell_range", "list_item", "code_block", "email_header", "email_body"
]


class ExtractedElement(BaseModel):
    type: ElementType
    text: str
    page: int | None = None
    slide: int | None = None
    sheet: str | None = None
    heading_level: int | None = None
    extra: dict[str, Any] = {}


class ExtractionMetadata(BaseModel):
    page_count: int | None = None
    sheet_names: list[str] = []
    slide_count: int | None = None
    author: str | None = None
    title: str | None = None
    created: str | None = None
    word_count: int = 0


class ExtractionResult(BaseModel):
    elements: list[ExtractedElement]
    metadata: ExtractionMetadata
    full_text: str
    extractor_name: str
    extractor_version: str


class BaseExtractor(ABC):
    name: str = "BaseExtractor"
    version: str = "1.0"

    @abstractmethod
    def can_handle(self, parser_type: str) -> bool: ...

    @abstractmethod
    def extract(self, content: bytes, filename: str) -> ExtractionResult: ...

    def extract_structure(self, content: bytes, filename: str) -> list[ExtractedElement]:
        """Convenience wrapper — most callers only need the element list."""
        return self.extract(content, filename).elements

    def extract_metadata(self, content: bytes, filename: str) -> ExtractionMetadata:
        return self.extract(content, filename).metadata
