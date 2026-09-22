from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.services.segmenter import SegmentDraft


@dataclass
class ChunkDraft:
    text: str
    segment_id: str | None
    section_title: str | None
    page_start: int | None
    page_end: int | None
    chunker_type: str


class BaseChunker(ABC):
    chunker_type: str = "BaseChunker"
    version: str = "1.1"

    @abstractmethod
    def chunk(self, segments: list[SegmentDraft]) -> list[ChunkDraft]: ...


def greedy_group(paragraphs: list[str], max_chars: int) -> list[str]:
    """Accumulates paragraphs into groups up to max_chars without ever
    splitting a paragraph mid-sentence — the one rule every text chunker
    here shares, regardless of how it decides segment boundaries."""
    groups: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if current and current_len + len(p) + 2 > max_chars:
            groups.append("\n\n".join(current))
            current, current_len = [p], len(p)
        else:
            current.append(p)
            current_len += len(p) + 2
    if current:
        groups.append("\n\n".join(current))
    return groups
