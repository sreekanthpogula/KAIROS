from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ClassifierInput:
    filename: str
    mime_type: str
    parser_type: str
    full_text: str
    headings: list[str]
    has_table: bool = False
    has_slide: bool = False


@dataclass
class ClassifierVote:
    ontology_id: str | None
    confidence: float
    signals: list[str]
    method: str
    scores: dict[str, float] = field(default_factory=dict)  # ontology_id -> raw score, for transparency


class BaseDocumentClassifier(ABC):
    method_name: str = "base"

    @abstractmethod
    def classify(self, doc: ClassifierInput) -> ClassifierVote: ...
