from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ClassificationSignal(BaseModel):
    signal: str
    matched: bool = True
    weight: float = 0.0


class ClassificationOutput(BaseModel):
    """Exact shape from spec section 12."""

    document_type: str
    document_subtype: Optional[str] = None
    domain: str
    confidence: float
    reasoning_signals: list[str]
    method: str = "hybrid"
    raw_scores: dict = {}
    ontology_id: Optional[str] = None
    confidence_action: str
    classifier_version: str
    ontology_version: str


class ClassificationResultRead(ClassificationOutput):
    id: str
    document_id: str
    is_current: bool
    created_at: str
