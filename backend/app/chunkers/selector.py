"""Chunker selection (spec section 19) — the decision that makes type-aware
chunking real rather than cosmetic.

Two factors, in priority order:

1. File STRUCTURE, when the format itself already implies a natural chunk
   boundary (a slide, a worksheet, a rows-and-columns table, an email).
   Semantics cannot override this — a slide deck about legal contracts is
   still chunked by slide, because that's how the content is organized.
2. Semantic document_type/ontology category, when the format is just
   flowing text (PDF/DOCX/HTML/TXT/MD) and offers no structural hint of
   its own — a contract-shaped PDF and a runbook-shaped PDF need different
   chunking even though both are "just a PDF".

See docs/chunking.md / ADR-003 for the full trade-off discussion (why not
pure format-based, why not pure semantic-based).
"""
from __future__ import annotations

from functools import lru_cache

from app.chunkers.base import BaseChunker
from app.chunkers.contract_chunker import ContractChunker
from app.chunkers.email_chunker import EmailChunker
from app.chunkers.generic_chunker import GenericChunker
from app.chunkers.presentation_chunker import PresentationChunker
from app.chunkers.spreadsheet_chunker import SpreadsheetChunker
from app.chunkers.technical_chunker import TechnicalDocumentChunker
from app.ontology.service import OntologyService

FORMAT_FORCED_CHUNKER: dict[str, str] = {
    "pptx": "presentation",
    "xlsx": "spreadsheet",
    "csv": "spreadsheet",
    "email": "email",
}


class ChunkerSelector:
    def __init__(self, ontology: OntologyService):
        self.ontology = ontology
        self._chunkers: dict[str, BaseChunker] = {
            "contract": ContractChunker(),
            "technical": TechnicalDocumentChunker(),
            "spreadsheet": SpreadsheetChunker(),
            "presentation": PresentationChunker(),
            "email": EmailChunker(),
            "generic": GenericChunker(),
        }

    def select(self, parser_type: str, ontology_id: str | None) -> BaseChunker:
        forced = FORMAT_FORCED_CHUNKER.get(parser_type)
        if forced:
            return self._chunkers[forced]
        hint = self.ontology.chunker_for(ontology_id) if ontology_id else "generic"
        return self._chunkers.get(hint, self._chunkers["generic"])


@lru_cache
def get_chunker_selector() -> ChunkerSelector:
    from app.ontology.service import get_ontology_service

    return ChunkerSelector(get_ontology_service())
