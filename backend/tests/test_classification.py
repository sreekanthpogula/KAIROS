"""Unit tests for the classification pipeline (spec section 12) using
HybridClassifier against the real synthetic sample corpus.

No DB needed: classification is pure input -> ClassificationOutput. These
tests replicate exactly what
PipelineOrchestrator._stage_classify does to build a ClassifierInput
(headings, has_table, has_slide) so the classifier sees the same shape of
input it would during a real ingestion.
"""
from __future__ import annotations

import pytest

from app.classifiers.base import ClassifierInput
from app.classifiers.factory import get_hybrid_classifier
from app.core.enums import ConfidenceAction
from app.extractors.registry import get_extractor
from app.services.file_detector import FileDetector
from app.schemas.classification import ClassificationOutput
from tests.conftest import load_golden_labels, read_sample_bytes

AMBIGUOUS_FILENAME = "ambiguous_mixed_memo.pdf"
MIN_CORPUS_ACCURACY = 0.90


def classify_sample(filename: str) -> ClassificationOutput:
    content = read_sample_bytes(filename)
    detection = FileDetector().detect(filename, content)
    extraction = get_extractor(detection.parser_type).extract(content, filename)
    headings = [e.text for e in extraction.elements if e.type == "heading"]
    classifier_input = ClassifierInput(
        filename=filename,
        mime_type=detection.mime_type,
        parser_type=detection.parser_type,
        full_text=extraction.full_text,
        headings=headings,
        has_table=any(e.type in ("table", "sheet") for e in extraction.elements),
        has_slide=any(e.type == "slide" for e in extraction.elements),
    )
    return get_hybrid_classifier().classify(classifier_input)


@pytest.mark.parametrize(
    "filename, expected_ontology_id",
    [
        ("provider_agreement_northvalley.pdf", "legal.contracts.provider_agreement"),
        ("hipaa_compliance_policy.pdf", "legal.compliance.hipaa_compliance_policy"),
        ("insurance_claim_report_q3.xlsx", "financial.claims.insurance_claim_report"),
        ("production_runbook_patient_portal.md", "technical.runbooks.production_runbook"),
        ("api_architecture_document.md", "technical.architecture.api_architecture_document"),
        ("provider_outreach_email.eml", "administrative.communications.provider_outreach_email"),
    ],
)
def test_unambiguous_sample_classifies_to_golden_ontology_id(filename, expected_ontology_id):
    output = classify_sample(filename)
    assert output.ontology_id == expected_ontology_id


def test_unambiguous_sample_lands_above_review_threshold():
    output = classify_sample("provider_agreement_northvalley.pdf")
    assert output.confidence_action in (ConfidenceAction.AUTO_ACCEPT.value, ConfidenceAction.SECONDARY_VALIDATION.value)


def test_ambiguous_memo_is_routed_to_review_not_forced_to_a_label():
    # This document is DELIBERATELY ambiguous (mixes signals from multiple
    # categories) and is expected to miss its "golden" label -- the
    # correct behavior is landing below the review threshold, not matching
    # any particular ontology_id.
    output = classify_sample(AMBIGUOUS_FILENAME)
    assert output.confidence_action == ConfidenceAction.REVIEW_REQUIRED.value


def test_full_corpus_achieves_at_least_90_percent_ontology_accuracy():
    golden_labels = load_golden_labels()
    assert len(golden_labels) > 0

    correct = 0
    misses = []
    for entry in golden_labels:
        output = classify_sample(entry["filename"])
        if output.ontology_id == entry["ontology_id"]:
            correct += 1
        else:
            misses.append((entry["filename"], entry["ontology_id"], output.ontology_id))

    accuracy = correct / len(golden_labels)
    assert accuracy >= MIN_CORPUS_ACCURACY, f"accuracy {accuracy:.3f}, misses: {misses}"

    # The one documented, expected miss is the deliberately ambiguous memo.
    miss_filenames = {m[0] for m in misses}
    assert miss_filenames <= {AMBIGUOUS_FILENAME}


def test_classification_output_has_traceability_versions():
    output = classify_sample("provider_agreement_northvalley.pdf")
    assert output.classifier_version
    assert output.ontology_version
    assert output.method in ("hybrid", "hybrid+llm")
