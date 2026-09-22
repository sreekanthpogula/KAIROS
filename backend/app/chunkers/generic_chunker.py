from __future__ import annotations

from app.chunkers.base import BaseChunker, ChunkDraft, greedy_group
from app.services.segmenter import SegmentDraft


class GenericChunker(BaseChunker):
    """Fallback: semantic paragraph grouping, no structural assumptions.
    Used for anything that isn't a contract, technical doc, spreadsheet,
    presentation, or email — e.g. invoices, forms, ad hoc memos."""

    chunker_type = "GenericChunker"
    MAX_CHARS = 800

    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for seg in segments:
            paragraphs = [e.text for e in seg.elements if e.text.strip()]
            if not paragraphs and seg.title:
                paragraphs = [seg.title]
            for group_text in greedy_group(paragraphs, self.MAX_CHARS):
                drafts.append(
                    ChunkDraft(
                        text=group_text, segment_id=seg.id, section_title=seg.title,
                        page_start=seg.page_start, page_end=seg.page_end, chunker_type=self.chunker_type,
                    )
                )
        return drafts
