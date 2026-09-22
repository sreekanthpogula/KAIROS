from __future__ import annotations

from app.chunkers.base import BaseChunker, ChunkDraft, greedy_group
from app.services.segmenter import SegmentDraft


class EmailChunker(BaseChunker):
    """Keeps header context (from/to/subject/date) attached to the body —
    a body-only chunk loses who sent it and when."""

    chunker_type = "EmailChunker"
    MAX_CHARS = 1200

    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for seg in segments:
            header = next((e.text for e in seg.elements if e.type == "email_header"), "")
            body = next((e.text for e in seg.elements if e.type == "email_body"), "")
            paragraphs = [header] + body.split("\n\n") if header else body.split("\n\n")
            for group_text in greedy_group(paragraphs, self.MAX_CHARS):
                drafts.append(
                    ChunkDraft(
                        text=group_text, segment_id=seg.id, section_title=seg.title,
                        page_start=None, page_end=None, chunker_type=self.chunker_type,
                    )
                )
        return drafts
