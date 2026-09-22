"""Unit tests for type-aware chunking (spec sections 19-20):

- app.chunkers.selector.ChunkerSelector -- which chunker a given
  (parser_type, ontology_id) combination resolves to.
- app.chunkers.technical_chunker.TechnicalDocumentChunker -- keeps a
  markdown code block as its own standalone chunk.
- app.models.chunk.Chunk.to_metadata_dict() -- exact key shape.

No DB needed anywhere in this file: ChunkerSelector is pure logic over the
real (read-only) OntologyService, the chunkers operate on in-memory
SegmentDraft objects, and Chunk is instantiated directly (never flushed).
"""
from __future__ import annotations

from app.chunkers.contract_chunker import ContractChunker
from app.chunkers.email_chunker import EmailChunker
from app.chunkers.generic_chunker import GenericChunker
from app.chunkers.presentation_chunker import PresentationChunker
from app.chunkers.selector import ChunkerSelector
from app.chunkers.spreadsheet_chunker import SpreadsheetChunker
from app.chunkers.technical_chunker import TechnicalDocumentChunker
from app.extractors.registry import get_extractor
from app.models.chunk import Chunk
from app.ontology.service import get_ontology_service
from app.services.segmenter import DocumentSegmenter
from tests.conftest import read_sample_bytes

CONTRACT_LEAF = "legal.contracts.provider_agreement"  # category chunker hint: contract
TECHNICAL_LEAF = "legal.compliance.hipaa_compliance_policy"  # category chunker hint: technical


def _selector() -> ChunkerSelector:
    return ChunkerSelector(get_ontology_service())


# --- ChunkerSelector: format always wins over semantics --------------------


def test_pptx_always_gets_presentation_chunker_even_with_contract_hint():
    selector = _selector()
    chunker = selector.select("pptx", CONTRACT_LEAF)
    assert isinstance(chunker, PresentationChunker)


def test_pptx_always_gets_presentation_chunker_with_no_ontology_hint():
    selector = _selector()
    chunker = selector.select("pptx", None)
    assert isinstance(chunker, PresentationChunker)


def test_xlsx_always_gets_spreadsheet_chunker_even_with_technical_hint():
    selector = _selector()
    chunker = selector.select("xlsx", TECHNICAL_LEAF)
    assert isinstance(chunker, SpreadsheetChunker)


def test_csv_always_gets_spreadsheet_chunker():
    selector = _selector()
    chunker = selector.select("csv", CONTRACT_LEAF)
    assert isinstance(chunker, SpreadsheetChunker)


def test_email_format_always_gets_email_chunker():
    selector = _selector()
    chunker = selector.select("email", TECHNICAL_LEAF)
    assert isinstance(chunker, EmailChunker)


# --- ChunkerSelector: flowing-text formats fall through to the semantic hint


def test_pdf_with_contract_ontology_hint_gets_contract_chunker():
    selector = _selector()
    chunker = selector.select("pdf", CONTRACT_LEAF)
    assert isinstance(chunker, ContractChunker)


def test_docx_with_contract_ontology_hint_gets_contract_chunker():
    selector = _selector()
    chunker = selector.select("docx", CONTRACT_LEAF)
    assert isinstance(chunker, ContractChunker)


def test_pdf_with_technical_ontology_hint_gets_technical_chunker():
    selector = _selector()
    chunker = selector.select("pdf", TECHNICAL_LEAF)
    assert isinstance(chunker, TechnicalDocumentChunker)


def test_pdf_with_unknown_ontology_id_falls_back_to_generic():
    selector = _selector()
    chunker = selector.select("pdf", "totally.invented.leaf")
    assert isinstance(chunker, GenericChunker)


def test_pdf_with_none_ontology_id_falls_back_to_generic():
    selector = _selector()
    chunker = selector.select("pdf", None)
    assert isinstance(chunker, GenericChunker)


# --- TechnicalDocumentChunker: code block isolation -------------------------


def test_technical_chunker_keeps_markdown_code_block_as_standalone_chunk():
    content = read_sample_bytes("api_architecture_document.md")
    extraction = get_extractor("markdown").extract(content, "api_architecture_document.md")
    segments = DocumentSegmenter().segment(extraction, "markdown")

    chunks = TechnicalDocumentChunker().chunk(segments)
    assert len(chunks) > 1  # more than just the code block

    code_chunks = [c for c in chunks if "GET /api/v1/patients" in c.text]
    assert len(code_chunks) == 1, "the code block must land in exactly one chunk"

    code_chunk = code_chunks[0]
    assert "POST /api/v1/appointments" in code_chunk.text
    # It must be genuinely standalone: no surrounding prose sentence, and no
    # section-title prefix (prose chunks from this chunker are prefixed with
    # "{section title}\n\n{text}" -- the code chunk deliberately is not).
    assert "All services expose" not in code_chunk.text
    assert "API Design" not in code_chunk.text

    # And the surrounding prose must not have swallowed the code block either.
    prose_chunks = [c for c in chunks if c is not code_chunk]
    assert all("GET /api/v1/patients" not in c.text for c in prose_chunks)
    assert any("All services expose" in c.text for c in prose_chunks)


# --- Chunk.to_metadata_dict(): exact key shape (spec section 20) -----------


def test_chunk_to_metadata_dict_has_exact_spec_keys():
    chunk = Chunk(
        id="chunk-1",
        document_id="doc-1",
        chunk_index=0,
        text="some chunk text",
        chunker_type="GenericChunker",
        chunker_version="1.1",
        section="Section 1",
        page_start=1,
        page_end=2,
        document_type="contract",
        document_subtype="provider_agreement",
        domain="legal",
        ontology_id="legal.contracts.provider_agreement",
        ontology_path="Healthcare/Legal/Contracts/Provider Agreement",
        classification_confidence=0.97,
        topics=["termination"],
        entities=["North Valley Hospital"],
        security_level="confidential",
        allowed_groups=["legal"],
        source_system="demo-sharepoint",
        source_uri=None,
        parser_version="1.0",
        classifier_version="1.2",
        ontology_version="1.0",
    )

    expected_keys = {
        "chunk_id", "document_id", "text", "document_type", "document_subtype",
        "domain", "ontology_path", "topics", "entities", "page_start", "page_end",
        "section", "classification_confidence", "security_level", "source_system",
        "source_uri", "parser_version", "classifier_version", "ontology_version",
    }

    result = chunk.to_metadata_dict()
    assert set(result.keys()) == expected_keys
    assert result["chunk_id"] == "chunk-1"
    assert result["text"] == "some chunk text"
    assert result["topics"] == ["termination"]


def test_chunk_to_metadata_dict_defaults_topics_and_entities_to_empty_list():
    chunk = Chunk(
        id="chunk-2", document_id="doc-1", chunk_index=0, text="text",
        chunker_type="GenericChunker", chunker_version="1.1", section=None,
        page_start=None, page_end=None, document_type=None, document_subtype=None,
        domain=None, ontology_id=None, ontology_path=None, classification_confidence=None,
        topics=None, entities=None, security_level="internal", allowed_groups=[],
        source_system=None, source_uri=None, parser_version=None, classifier_version=None,
        ontology_version=None,
    )
    result = chunk.to_metadata_dict()
    assert result["topics"] == []
    assert result["entities"] == []
