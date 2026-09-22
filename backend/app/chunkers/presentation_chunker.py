from __future__ import annotations

from app.chunkers.base import BaseChunker, ChunkDraft
from app.services.segmenter import SegmentDraft


class PresentationChunker(BaseChunker):
    """Chunks by slide — the natural retrieval unit for a deck. Title and
    body are kept together since a bullet list is meaningless without the
    slide title framing it."""

    chunker_type = "PresentationChunker"

    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for seg in segments:
            body = "\n\n".join(e.text for e in seg.elements if e.type != "heading" and e.text.strip())
            text = f"{seg.title}\n\n{body}" if body else (seg.title or "")
            if not text.strip():
                continue
            drafts.append(
                ChunkDraft(
                    text=text, segment_id=seg.id, section_title=seg.title,
                    page_start=seg.page_start, page_end=seg.page_end, chunker_type=self.chunker_type,
                )
            )
        return drafts
