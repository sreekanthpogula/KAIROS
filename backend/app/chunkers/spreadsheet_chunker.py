from __future__ import annotations

from app.chunkers.base import BaseChunker, ChunkDraft
from app.services.segmenter import SegmentDraft


class SpreadsheetChunker(BaseChunker):
    """Chunks by logical table, not by character count. Splits large
    sheets into row batches, repeating the header row in every batch so
    each chunk is independently interpretable — a chunk of claim rows
    without the header row is just numbers."""

    chunker_type = "SpreadsheetChunker"
    ROWS_PER_CHUNK = 25

    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for seg in segments:
            sheet_element = next((e for e in seg.elements if e.type in ("sheet", "table")), None)
            if sheet_element is None:
                continue

            headers = sheet_element.extra.get("headers", [])
            rows = sheet_element.extra.get("rows", [])
            header_line = " | ".join(str(h) for h in headers)

            if not rows:
                drafts.append(
                    ChunkDraft(
                        text=f"Sheet: {seg.title}\n{sheet_element.text}", segment_id=seg.id, section_title=seg.title,
                        page_start=None, page_end=None, chunker_type=self.chunker_type,
                    )
                )
                continue

            for i in range(0, len(rows), self.ROWS_PER_CHUNK):
                batch = rows[i : i + self.ROWS_PER_CHUNK]
                body = "\n".join([header_line] + [" | ".join(str(c) for c in r) for r in batch])
                drafts.append(
                    ChunkDraft(
                        text=f"Sheet: {seg.title} (rows {i + 1}-{i + len(batch)})\n{body}",
                        segment_id=seg.id, section_title=seg.title,
                        page_start=None, page_end=None, chunker_type=self.chunker_type,
                    )
                )
        return drafts
