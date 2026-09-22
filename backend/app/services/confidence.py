"""Confidence-based routing (spec section 14). Thresholds are configurable
via Settings, never hard-coded at call sites."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.enums import ConfidenceAction


class ConfidenceService:
    def __init__(self, settings: Settings):
        self.auto_accept = settings.confidence_auto_accept
        self.secondary_validation = settings.confidence_secondary_validation

    def action_for(self, confidence: float) -> str:
        if confidence >= self.auto_accept:
            return ConfidenceAction.AUTO_ACCEPT.value
        if confidence >= self.secondary_validation:
            return ConfidenceAction.SECONDARY_VALIDATION.value
        return ConfidenceAction.REVIEW_REQUIRED.value


@lru_cache
def get_confidence_service() -> ConfidenceService:
    return ConfidenceService(get_settings())
