from __future__ import annotations

from functools import lru_cache

from app.extractors.base import BaseExtractor
from app.extractors.docx_extractor import DOCXExtractor
from app.extractors.email_extractor import EmailExtractor
from app.extractors.html_extractor import HTMLExtractor
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.pptx_extractor import PPTXExtractor
from app.extractors.text_extractor import TextExtractor
from app.extractors.xlsx_extractor import XLSXExtractor


class UnsupportedFileTypeError(Exception):
    pass


@lru_cache
def _extractors() -> tuple[BaseExtractor, ...]:
    return (
        PDFExtractor(),
        DOCXExtractor(),
        XLSXExtractor(),
        PPTXExtractor(),
        HTMLExtractor(),
        TextExtractor(),
        EmailExtractor(),
    )


def get_extractor(parser_type: str) -> BaseExtractor:
    for extractor in _extractors():
        if extractor.can_handle(parser_type):
            return extractor
    raise UnsupportedFileTypeError(f"No extractor registered for parser_type={parser_type!r}")
