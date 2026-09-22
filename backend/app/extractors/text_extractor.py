from __future__ import annotations

import csv
import io
from pathlib import Path

from app.extractors.base import BaseExtractor, ExtractedElement, ExtractionMetadata, ExtractionResult


class TextExtractor(BaseExtractor):
    """Handles plain text, Markdown, and CSV — three formats that share no
    binary structure to parse, just a decode + light heuristics."""

    name = "TextExtractor"
    version = "1.0"

    def can_handle(self, parser_type: str) -> bool:
        return parser_type in ("text", "markdown", "csv")

    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        ext = Path(filename).suffix.lower()
        # Raw bytes carry whatever line ending the source used (CRLF on
        # Windows-authored files); normalize so block/line splitting below
        # doesn't silently collapse into one block on "\n\n" boundaries.
        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")

        if ext == ".csv":
            return self._extract_csv(text)
        if ext == ".md":
            return self._extract_markdown(text)
        return self._extract_plain(text)

    # ------------------------------------------------------------------ #
    def _extract_plain(self, text: str) -> ExtractionResult:
        elements: list[ExtractedElement] = []
        full_text_parts: list[str] = []
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        for block in blocks:
            lines = block.splitlines()
            first_line = lines[0].strip()
            is_heading = len(lines) == 1 and (
                first_line.endswith(":") or (first_line.isupper() and len(first_line) < 80)
            )
            elements.append(
                ExtractedElement(type="heading" if is_heading else "paragraph", text=first_line if is_heading else block)
            )
            full_text_parts.append(block)
        metadata = ExtractionMetadata(word_count=sum(len(t.split()) for t in full_text_parts))
        return ExtractionResult(
            elements=elements, metadata=metadata, full_text="\n\n".join(full_text_parts),
            extractor_name=self.name, extractor_version=self.version,
        )

    def _extract_markdown(self, text: str) -> ExtractionResult:
        elements: list[ExtractedElement] = []
        full_text_parts: list[str] = []
        code_fence_open = False
        code_buffer: list[str] = []
        paragraph_buffer: list[str] = []

        def flush_paragraph():
            if paragraph_buffer:
                joined = "\n".join(paragraph_buffer).strip()
                if joined:
                    elements.append(ExtractedElement(type="paragraph", text=joined))
                    full_text_parts.append(joined)
                paragraph_buffer.clear()

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.strip().startswith("```"):
                if code_fence_open:
                    joined = "\n".join(code_buffer)
                    elements.append(ExtractedElement(type="code_block", text=joined))
                    full_text_parts.append(joined)
                    code_buffer = []
                code_fence_open = not code_fence_open
                continue
            if code_fence_open:
                code_buffer.append(line)
                continue
            stripped = line.strip()
            if not stripped:
                flush_paragraph()
                continue
            if stripped.startswith("#"):
                flush_paragraph()
                level = len(stripped) - len(stripped.lstrip("#"))
                heading_text = stripped.lstrip("#").strip()
                elements.append(ExtractedElement(type="heading", text=heading_text, heading_level=min(level, 6)))
                full_text_parts.append(heading_text)
            elif stripped.startswith(("- ", "* ")):
                flush_paragraph()
                item_text = stripped[2:].strip()
                elements.append(ExtractedElement(type="list_item", text=item_text))
                full_text_parts.append(item_text)
            else:
                paragraph_buffer.append(stripped)
        flush_paragraph()

        metadata = ExtractionMetadata(word_count=sum(len(t.split()) for t in full_text_parts))
        return ExtractionResult(
            elements=elements, metadata=metadata, full_text="\n\n".join(full_text_parts),
            extractor_name=self.name, extractor_version=self.version,
        )

    def _extract_csv(self, text: str) -> ExtractionResult:
        reader = csv.reader(io.StringIO(text))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        elements: list[ExtractedElement] = []
        full_text_parts: list[str] = []
        if rows:
            headers, data_rows = rows[0], rows[1:]
            rendered = "\n".join([" | ".join(headers)] + [" | ".join(r) for r in data_rows[:300]])
            elements.append(
                ExtractedElement(type="table", text=rendered, extra={"headers": headers, "rows": data_rows, "row_count": len(data_rows)})
            )
            full_text_parts.append(rendered)
        metadata = ExtractionMetadata(word_count=sum(len(t.split()) for t in full_text_parts))
        return ExtractionResult(
            elements=elements, metadata=metadata, full_text="\n\n".join(full_text_parts),
            extractor_name=self.name, extractor_version=self.version,
        )
