"""Splits an extracted document into structural/semantic segments (spec
section 18). A document is never assumed to be one unit — a contract has
sections, a deck has slides, a workbook has sheets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.ids import new_id
from app.extractors.base import ExtractedElement, ExtractionResult


@dataclass
class SegmentDraft:
    id: str
    title: str | None
    segment_type: str
    level: int
    parent_id: str | None
    order_index: int
    page_start: int | None
    page_end: int | None
    elements: list[ExtractedElement] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(e.text for e in self.elements if e.text.strip())


class DocumentSegmenter:
    def segment(self, extraction: ExtractionResult, parser_type: str) -> list[SegmentDraft]:
        if any(e.type == "slide" for e in extraction.elements):
            return self._segment_by_slide(extraction.elements)
        if any(e.type == "sheet" for e in extraction.elements):
            return self._segment_by_sheet(extraction.elements)
        if parser_type == "email":
            return self._segment_email(extraction.elements)
        return self._segment_by_heading(extraction.elements)

    # ------------------------------------------------------------------ #
    def _segment_by_slide(self, elements: list[ExtractedElement]) -> list[SegmentDraft]:
        by_slide: dict[int, list[ExtractedElement]] = {}
        for e in elements:
            slide_no = e.slide or 0
            by_slide.setdefault(slide_no, []).append(e)

        drafts = []
        for order, slide_no in enumerate(sorted(by_slide)):
            els = by_slide[slide_no]
            title = next((e.text for e in els if e.type == "heading"), f"Slide {slide_no}")
            drafts.append(
                SegmentDraft(
                    id=new_id(), title=title, segment_type="slide", level=1, parent_id=None,
                    order_index=order, page_start=slide_no, page_end=slide_no, elements=els,
                )
            )
        return drafts

    def _segment_by_sheet(self, elements: list[ExtractedElement]) -> list[SegmentDraft]:
        drafts = []
        for order, e in enumerate(el for el in elements if el.type == "sheet"):
            drafts.append(
                SegmentDraft(
                    id=new_id(), title=e.sheet or f"Sheet {order + 1}", segment_type="sheet", level=1,
                    parent_id=None, order_index=order, page_start=None, page_end=None, elements=[e],
                )
            )
        return drafts

    def _segment_email(self, elements: list[ExtractedElement]) -> list[SegmentDraft]:
        subject = next((e.text for e in elements if e.type == "heading"), "Email")
        return [
            SegmentDraft(
                id=new_id(), title=subject, segment_type="email", level=1, parent_id=None,
                order_index=0, page_start=None, page_end=None, elements=elements,
            )
        ]

    def _segment_by_heading(self, elements: list[ExtractedElement]) -> list[SegmentDraft]:
        drafts: list[SegmentDraft] = []
        stack: list[SegmentDraft] = []  # open headings, index 0 = level-1
        order = 0

        def new_segment(title: str | None, level: int, page: int | None) -> SegmentDraft:
            nonlocal order
            parent = None
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                parent = stack[-1].id
            draft = SegmentDraft(
                id=new_id(), title=title, segment_type="section", level=level, parent_id=parent,
                order_index=order, page_start=page, page_end=page,
            )
            order += 1
            drafts.append(draft)
            stack.append(draft)
            return draft

        current: SegmentDraft | None = None
        for e in elements:
            if e.type == "heading":
                current = new_segment(e.text, e.heading_level or 1, e.page)
            else:
                if current is None:
                    current = new_segment("Document Body", 1, e.page)
                current.elements.append(e)
                if e.page is not None:
                    current.page_start = e.page if current.page_start is None else min(current.page_start, e.page)
                    current.page_end = e.page if current.page_end is None else max(current.page_end, e.page)

        return drafts
