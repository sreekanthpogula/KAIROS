from __future__ import annotations

from app.chunkers.base import BaseChunker, ChunkDraft, greedy_group
from app.services.segmenter import SegmentDraft


class ContractChunker(BaseChunker):
    """Chunks by clause/section. Contracts get a larger max size than
    generic text because clauses often only make sense read together
    (e.g. a termination clause referencing defined terms) — see
    docs/chunking.md. Each chunk carries its section heading inline so a
    standalone chunk retrieved later ("Section 4: Termination...") is
    still self-explanatory without the parent document."""

    chunker_type = "ContractChunker"
    MAX_CHARS = 1500

    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for seg in segments:
            paragraphs = [e.text for e in seg.elements if e.text.strip()]
            if not paragraphs:
                continue
            for group_text in greedy_group(paragraphs, self.MAX_CHARS):
                text = f"{seg.title}\n\n{group_text}" if seg.title else group_text
                drafts.append(
                    ChunkDraft(
                        text=text, segment_id=seg.id, section_title=seg.title,
                        page_start=seg.page_start, page_end=seg.page_end, chunker_type=self.chunker_type,
                    )
                )
        return drafts
