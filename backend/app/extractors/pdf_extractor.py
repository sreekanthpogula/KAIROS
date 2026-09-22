from __future__ import annotations

import fitz  # PyMuPDF

from app.extractors.base import BaseExtractor, ExtractedElement, ExtractionMetadata, ExtractionResult


class PDFExtractor(BaseExtractor):
    """Extracts headings/paragraphs/tables from PDFs, page-anchored.

    Heading detection is a font-size heuristic (spans >= HEADING_SIZE_PT are
    headings). This is a POC trade-off: it works reliably for the
    consistently-styled synthetic corpus but would need a more robust
    layout model (or OCR + layout analysis) for arbitrary scanned PDFs in
    production — see docs/chunking.md.
    """

    name = "PDFExtractor"
    version = "1.0"
    HEADING_SIZE_PT = 12.5

    def can_handle(self, parser_type: str) -> bool:
        return parser_type == "pdf"

    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        doc = fitz.open(stream=content, filetype="pdf")
        elements: list[ExtractedElement] = []
        full_text_parts: list[str] = []

        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_num = page_index + 1
                self._extract_page_text(page, page_num, elements, full_text_parts)
                self._extract_page_tables(page, page_num, elements, full_text_parts)

            meta = doc.metadata or {}
            metadata = ExtractionMetadata(
                page_count=len(doc),
                title=meta.get("title") or None,
                author=meta.get("author") or None,
                created=meta.get("creationDate") or None,
                word_count=sum(len(t.split()) for t in full_text_parts),
            )
        finally:
            doc.close()

        return ExtractionResult(
            elements=elements,
            metadata=metadata,
            full_text="\n\n".join(full_text_parts),
            extractor_name=self.name,
            extractor_version=self.version,
        )

    def _extract_page_text(self, page, page_num, elements, full_text_parts) -> None:
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            lines_text: list[str] = []
            max_size = 0.0
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(span.get("text", "") for span in spans)
                if line_text.strip():
                    lines_text.append(line_text)
                for span in spans:
                    max_size = max(max_size, span.get("size", 0.0))
            block_text = "\n".join(lines_text).strip()
            if not block_text:
                continue
            is_heading = max_size >= self.HEADING_SIZE_PT and len(block_text) < 120 and "\n" not in block_text
            elements.append(
                ExtractedElement(
                    type="heading" if is_heading else "paragraph",
                    text=block_text,
                    page=page_num,
                    heading_level=1 if is_heading else None,
                )
            )
            full_text_parts.append(block_text)

    def _extract_page_tables(self, page, page_num, elements, full_text_parts) -> None:
        try:
            finder = page.find_tables()
            tables = list(finder.tables) if finder else []
        except Exception:
            tables = []
        for t_index, table in enumerate(tables):
            try:
                rows = table.extract()
            except Exception:
                continue
            rows = [[("" if cell is None else str(cell)) for cell in row] for row in rows]
            if not rows:
                continue
            rendered = "\n".join(" | ".join(r) for r in rows)
            elements.append(
                ExtractedElement(
                    type="table",
                    text=rendered,
                    page=page_num,
                    extra={"rows": rows, "table_index": t_index},
                )
            )
            full_text_parts.append(rendered)
