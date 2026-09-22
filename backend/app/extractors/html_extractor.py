from __future__ import annotations

from bs4 import BeautifulSoup

from app.extractors.base import BaseExtractor, ExtractedElement, ExtractionMetadata, ExtractionResult


class HTMLExtractor(BaseExtractor):
    name = "HTMLExtractor"
    version = "1.0"

    def can_handle(self, parser_type: str) -> bool:
        return parser_type == "html"

    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        soup = BeautifulSoup(content, "lxml")
        elements: list[ExtractedElement] = []
        full_text_parts: list[str] = []

        title = soup.title.get_text(strip=True) if soup.title else None
        body = soup.body or soup

        for el in body.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table"], recursive=True):
            if el.find_parent("table") and el.name != "table":
                continue  # avoid double-counting text inside table cells
            if el.name == "table":
                rows = []
                for tr in el.find_all("tr"):
                    cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append(cells)
                if not rows:
                    continue
                rendered = "\n".join(" | ".join(r) for r in rows)
                elements.append(ExtractedElement(type="table", text=rendered, extra={"rows": rows}))
                full_text_parts.append(rendered)
                continue

            text = el.get_text(strip=True)
            if not text:
                continue
            if el.name.startswith("h") and el.name[1:].isdigit():
                elements.append(ExtractedElement(type="heading", text=text, heading_level=int(el.name[1])))
            elif el.name == "li":
                elements.append(ExtractedElement(type="list_item", text=text))
            else:
                elements.append(ExtractedElement(type="paragraph", text=text))
            full_text_parts.append(text)

        metadata = ExtractionMetadata(title=title, word_count=sum(len(t.split()) for t in full_text_parts))

        return ExtractionResult(
            elements=elements,
            metadata=metadata,
            full_text="\n\n".join(full_text_parts),
            extractor_name=self.name,
            extractor_version=self.version,
        )
