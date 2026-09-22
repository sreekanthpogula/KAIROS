"""Unit tests for app.ontology.service.OntologyService (spec section 13).

Uses the real backend/app/ontology_data/healthcare_ontology.yaml via get_ontology_service()
(a stateless, read-only, @lru_cache'd singleton) — no DB needed.
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.ontology.service import get_ontology_service


@pytest.fixture()
def ontology():
    return get_ontology_service()


# --- Controlled classification enforcement (spec section 13) --------------


def test_resolve_or_none_returns_none_for_invented_id(ontology):
    assert ontology.resolve_or_none("legal.contracts.made_up_leaf_id") is None


def test_resolve_or_none_returns_none_for_completely_unknown_id(ontology):
    assert ontology.resolve_or_none("not.a.real.ontology.id") is None


def test_resolve_or_none_returns_node_for_real_leaf(ontology):
    node = ontology.resolve_or_none("legal.contracts.provider_agreement")
    assert node is not None
    assert node.id == "legal.contracts.provider_agreement"
    assert node.level == "type"


def test_resolve_or_none_rejects_non_leaf_domain_id(ontology):
    # "legal" is a domain node, not a controlled leaf -- must not resolve.
    assert ontology.resolve_or_none("legal") is None


def test_resolve_or_none_rejects_non_leaf_category_id(ontology):
    # "legal.contracts" is a category node, not a leaf type.
    assert ontology.resolve_or_none("legal.contracts") is None


# --- path_for / domain_of / document_type_for ------------------------------


def test_path_for_provider_agreement():
    ontology = get_ontology_service()
    assert ontology.path_for("legal.contracts.provider_agreement") == [
        "Healthcare",
        "Legal",
        "Contracts",
        "Provider Agreement",
    ]


def test_path_for_unknown_id_returns_empty_list(ontology):
    assert ontology.path_for("nonexistent.leaf") == []


def test_domain_of_provider_agreement_is_legal(ontology):
    domain_node = ontology.domain_of("legal.contracts.provider_agreement")
    assert domain_node is not None
    assert domain_node.id == "legal"
    assert domain_node.level == "domain"


def test_domain_of_clinical_leaf_is_clinical(ontology):
    domain_node = ontology.domain_of("clinical.clinical_guidelines.patient_care_guideline")
    assert domain_node is not None
    assert domain_node.id == "clinical"


def test_domain_of_unknown_id_returns_none(ontology):
    assert ontology.domain_of("nonexistent.leaf") is None


@pytest.mark.parametrize(
    "ontology_id, expected_document_type",
    [
        ("legal.contracts.provider_agreement", "contract"),
        ("legal.compliance.hipaa_compliance_policy", "compliance_policy"),
        ("financial.invoices.hospital_invoice", "invoice"),
        ("technical.runbooks.production_runbook", "runbook"),
    ],
)
def test_document_type_for_known_leaves(ontology, ontology_id, expected_document_type):
    assert ontology.document_type_for(ontology_id) == expected_document_type


def test_document_subtype_for_is_last_id_segment(ontology):
    assert ontology.document_subtype_for("legal.contracts.provider_agreement") == "provider_agreement"


# --- security_defaults_for --------------------------------------------------


def test_security_defaults_for_provider_agreement_is_confidential(ontology):
    level, groups = ontology.security_defaults_for("legal.contracts.provider_agreement")
    assert level == "confidential"
    assert "legal" in groups


def test_security_defaults_for_clinical_leaf_is_restricted(ontology):
    level, groups = ontology.security_defaults_for("clinical.clinical_guidelines.patient_care_guideline")
    assert level == "restricted"
    assert "clinical" in groups


def test_security_defaults_for_unknown_id_falls_back_to_settings_default(ontology):
    settings = get_settings()
    level, groups = ontology.security_defaults_for("totally.invented.id")
    assert level == settings.default_security_level
    assert groups == ["employee"]


# --- chunker hints / leaf enumeration ---------------------------------------


def test_chunker_for_contract_leaf_is_contract(ontology):
    assert ontology.chunker_for("legal.contracts.provider_agreement") == "contract"


def test_chunker_for_unknown_id_defaults_to_generic(ontology):
    assert ontology.chunker_for("nonexistent.leaf") == "generic"


def test_all_types_returns_only_leaf_level_nodes(ontology):
    leaves = ontology.all_types()
    assert len(leaves) > 0
    assert all(n.level == "type" for n in leaves)
    ids = {n.id for n in leaves}
    assert "legal.contracts.provider_agreement" in ids
    assert "legal" not in ids  # a domain id must not appear among leaves
    assert "legal.contracts" not in ids  # neither must a category id


def test_is_leaf_true_for_type_false_for_domain(ontology):
    assert ontology.is_leaf("legal.contracts.provider_agreement") is True
    assert ontology.is_leaf("legal") is False
    assert ontology.is_leaf("legal.contracts") is False
    assert ontology.is_leaf("nonexistent.leaf") is False
