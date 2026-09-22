from __future__ import annotations

from email import message_from_bytes
from email.policy import default as email_default_policy

from app.extractors.base import BaseExtractor, ExtractedElement, ExtractionMetadata, ExtractionResult


class EmailExtractor(BaseExtractor):
    """Standard-library `email` parsing (.eml) — no third-party dependency
    needed for header/body extraction."""

    name = "EmailExtractor"
    version = "1.0"

    def can_handle(self, parser_type: str) -> bool:
        return parser_type == "email"

    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        msg = message_from_bytes(content, policy=email_default_policy)

        sender = str(msg["from"] or "")
        to = str(msg["to"] or "")
        subject = str(msg["subject"] or "(no subject)")
        date = str(msg["date"] or "")

        header_text = f"From: {sender}\nTo: {to}\nSubject: {subject}\nDate: {date}"

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()
        body = (body or "").strip()

        elements = [
            ExtractedElement(
                type="email_header",
                text=header_text,
                extra={"from": sender, "to": to, "subject": subject, "date": date},
            ),
            ExtractedElement(type="heading", text=subject, heading_level=1),
            ExtractedElement(type="email_body", text=body),
        ]

        metadata = ExtractionMetadata(title=subject, author=sender, created=date, word_count=len(body.split()))

        return ExtractionResult(
            elements=elements,
            metadata=metadata,
            full_text=f"{header_text}\n\n{body}",
            extractor_name=self.name,
            extractor_version=self.version,
        )
