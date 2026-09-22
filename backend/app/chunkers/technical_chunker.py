from __future__ import annotations

from app.chunkers.base import BaseChunker, ChunkDraft, greedy_group
from app.services.segmenter import SegmentDraft


class TechnicalDocumentChunker(BaseChunker):
    """Chunks by heading/subsection, and keeps code blocks as their own
    standalone chunk rather than folding them into surrounding prose —
    splitting a code sample across two chunks makes both useless."""

    chunker_type = "TechnicalDocumentChunker"
    MAX_CHARS = 1000

    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for seg in segments:
            prose_buffer: list[str] = []

            def flush() -> None:
                for group_text in greedy_group(prose_buffer, self.MAX_CHARS):
                    text = f"{seg.title}\n\n{group_text}" if seg.title else group_text
                    drafts.append(
                        ChunkDraft(
                            text=text, segment_id=seg.id, section_title=seg.title,
                            page_start=seg.page_start, page_end=seg.page_end, chunker_type=self.chunker_type,
                        )
                    )
                prose_buffer.clear()

            for e in seg.elements:
                if not e.text.strip():
                    continue
                if e.type == "code_block":
                    flush()
                    drafts.append(
                        ChunkDraft(
                            text=e.text, segment_id=seg.id, section_title=seg.title,
                            page_start=seg.page_start, page_end=seg.page_end, chunker_type=self.chunker_type,
                        )
                    )
                else:
                    prose_buffer.append(e.text)
            flush()
        return drafts
