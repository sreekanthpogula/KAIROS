"""Synthetic named-entity extraction (spec section 16).

Provider-independent by design: BaseEntityExtractor defines the contract,
RuleBasedEntityExtractor is the DEMO_MODE implementation (gazetteer +
regex, zero network calls), and an LLM-backed implementation could be
dropped in behind the same interface for LLM_MODE without touching any
caller.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

_MONEY_RE = re.compile(r"\$[0-9][0-9,]*(?:\.[0-9]{2})?")
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_LONG_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b"
)
_PHYSICIAN_RE = re.compile(r"\bDr\.\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?\b")

_ORGANIZATIONS = ["North Valley Hospital", "Meridian Health Partners", "Summit Care Network"]
_DEPARTMENTS = [
    "Provider Network Management", "Provider Relations", "Provider Management", "Network Management",
    "Human Resources", "Finance", "Privacy Officer", "Platform Engineering", "Billing Department",
    "Reimbursement Review Committee", "Credentialing Committee",
]
_REGULATIONS = [
    "HIPAA", "Privacy Rule", "Security Rule", "Breach Notification Rule", "Medicare Advantage",
    "Medicaid", "CMS",
]
_PERSONS = ["Jordan Ellis", "Priya Natarajan", "Sam Whitfield"]


@dataclass
class ExtractedEntity:
    entity_type: str
    value: str
    normalized_value: str
    confidence: float = 0.85


class BaseEntityExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> list[ExtractedEntity]: ...


class RuleBasedEntityExtractor(BaseEntityExtractor):
    def extract(self, text: str) -> list[ExtractedEntity]:
        found: dict[tuple[str, str], ExtractedEntity] = {}

        def add(entity_type: str, value: str, normalized: str, confidence: float = 0.9) -> None:
            key = (entity_type, normalized)
            if key not in found:
                found[key] = ExtractedEntity(entity_type=entity_type, value=value, normalized_value=normalized, confidence=confidence)

        for org in _ORGANIZATIONS:
            if org.lower() in text.lower():
                add("organization", org, org, 0.95)

        for dept in _DEPARTMENTS:
            if dept.lower() in text.lower():
                add("department", dept, dept, 0.9)

        for reg in _REGULATIONS:
            if reg.lower() in text.lower():
                add("regulation", reg, reg.upper() if len(reg) <= 5 else reg, 0.9)

        for person in _PERSONS:
            if person.lower() in text.lower():
                add("person", person, person, 0.85)

        for match in _PHYSICIAN_RE.finditer(text):
            add("provider", match.group(0), match.group(0), 0.8)

        for match in _MONEY_RE.finditer(text):
            raw = match.group(0)
            normalized = raw.replace("$", "").replace(",", "")
            add("monetary_value", raw, normalized, 0.95)

        for match in _ISO_DATE_RE.finditer(text):
            add("date", match.group(0), match.group(0), 0.95)

        for match in _LONG_DATE_RE.finditer(text):
            month, day, year = match.groups()
            normalized = f"{int(year):04d}-{_MONTHS[month.lower()]:02d}-{int(day):02d}"
            add("date", match.group(0), normalized, 0.9)

        return list(found.values())


_extractor: BaseEntityExtractor | None = None


def get_entity_extractor() -> BaseEntityExtractor:
    global _extractor
    if _extractor is None:
        _extractor = RuleBasedEntityExtractor()
    return _extractor
