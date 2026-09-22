"""Unit tests for app.services.confidence.ConfidenceService (spec section 14).

Boundary tests around the AUTO_ACCEPT / SECONDARY_VALIDATION / REVIEW_REQUIRED
thresholds, plus a check that the thresholds are actually read from Settings
rather than hard-coded at the call site.

Note: Settings fields declare an explicit alias (e.g. CONFIDENCE_AUTO_ACCEPT)
and the model config does not set populate_by_name=True, so constructing a
custom Settings() in-test must use the alias/env-var name, not the
lower_snake_case field name.
"""
from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.enums import ConfidenceAction
from app.services.confidence import ConfidenceService


def _service_with(auto_accept: float, secondary_validation: float) -> ConfidenceService:
    settings = Settings(
        CONFIDENCE_AUTO_ACCEPT=auto_accept,
        CONFIDENCE_SECONDARY_VALIDATION=secondary_validation,
    )
    return ConfidenceService(settings)


def test_default_settings_thresholds_are_90_and_70():
    # Sanity check the defaults the rest of this file's boundary math relies on.
    settings = get_settings()
    assert settings.confidence_auto_accept == 0.90
    assert settings.confidence_secondary_validation == 0.70


def test_exactly_at_auto_accept_threshold_is_auto_accept():
    service = _service_with(0.90, 0.70)
    assert service.action_for(0.90) == ConfidenceAction.AUTO_ACCEPT.value


def test_just_below_auto_accept_threshold_is_secondary_validation():
    service = _service_with(0.90, 0.70)
    assert service.action_for(0.8999) == ConfidenceAction.SECONDARY_VALIDATION.value


def test_exactly_at_secondary_validation_threshold_is_secondary_validation():
    service = _service_with(0.90, 0.70)
    assert service.action_for(0.70) == ConfidenceAction.SECONDARY_VALIDATION.value


def test_just_below_secondary_validation_threshold_is_review_required():
    service = _service_with(0.90, 0.70)
    assert service.action_for(0.6999) == ConfidenceAction.REVIEW_REQUIRED.value


def test_confidence_of_1_0_is_auto_accept():
    service = _service_with(0.90, 0.70)
    assert service.action_for(1.0) == ConfidenceAction.AUTO_ACCEPT.value


def test_confidence_of_0_0_is_review_required():
    service = _service_with(0.90, 0.70)
    assert service.action_for(0.0) == ConfidenceAction.REVIEW_REQUIRED.value


def test_thresholds_are_read_from_settings_not_hardcoded():
    # Same raw confidence score, two different Settings instances -> two
    # different routing decisions. If the thresholds were hard-coded
    # constants in ConfidenceService instead of read off `settings`, both
    # instances below would produce the same action for 0.60.
    lenient = _service_with(auto_accept=0.50, secondary_validation=0.30)
    strict = _service_with(auto_accept=0.95, secondary_validation=0.90)

    assert lenient.action_for(0.60) == ConfidenceAction.AUTO_ACCEPT.value
    assert strict.action_for(0.60) == ConfidenceAction.REVIEW_REQUIRED.value


def test_custom_thresholds_move_the_secondary_validation_boundary_too():
    service = _service_with(auto_accept=0.99, secondary_validation=0.20)
    assert service.action_for(0.20) == ConfidenceAction.SECONDARY_VALIDATION.value
    assert service.action_for(0.1999) == ConfidenceAction.REVIEW_REQUIRED.value
