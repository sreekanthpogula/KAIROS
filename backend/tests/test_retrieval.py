"""Tests for hybrid retrieval + ACL filtering (spec sections 23-24, 28).

RetrievalService._is_allowed unit tests need no DB at all. The
group-membership / domain-filter tests ingest the real sample corpus once
per module (expensive: runs the full pipeline for 18 documents) into an
isolated test database, then run several read-only searches against it.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.retrieval.factory import get_retrieval_service
from app.retrieval.service import RetrievalService
from tests.conftest import SessionLocal, ingest_sample_corpus, reset_db


# --- RetrievalService._is_allowed: pure unit tests, no DB ------------------


def test_is_allowed_true_when_requester_group_in_allowed_groups():
    chunk = SimpleNamespace(allowed_groups=["legal", "executive"])
    assert RetrievalService._is_allowed(chunk, "legal") is True


def test_is_allowed_false_when_requester_group_not_in_allowed_groups():
    chunk = SimpleNamespace(allowed_groups=["legal", "executive"])
    assert RetrievalService._is_allowed(chunk, "engineering") is False


def test_is_allowed_false_for_unrelated_group_on_clinical_chunk():
    chunk = SimpleNamespace(allowed_groups=["clinical", "executive"])
    assert RetrievalService._is_allowed(chunk, "finance") is False


def test_is_allowed_defaults_open_when_allowed_groups_is_empty():
    # Documented current behavior: an empty allowed_groups list means "no
    # restriction configured" rather than "allow nobody". In practice every
    # real chunk gets a non-empty allowed_groups from
    # OntologyService.security_defaults_for (which itself falls back to
    # ["employee"]), so this branch is a defensive default, not something
    # reachable via the normal ingestion path.
    chunk = SimpleNamespace(allowed_groups=[])
    assert RetrievalService._is_allowed(chunk, "anyone_at_all") is True


# --- Full-corpus retrieval + ACL enforcement -------------------------------


@pytest.fixture(scope="module")
def ingested_db():
    """Ingests the full sample corpus once for this module, into its own
    freshly reset test database, and yields a Session other tests in this
    module can issue read-only queries against."""
    reset_db()
    session = SessionLocal()
    try:
        ingest_sample_corpus(session)
        yield session
    finally:
        session.close()


def test_requester_group_outside_allowed_groups_never_gets_chunk_back(ingested_db):
    service = get_retrieval_service()

    result = service.search(
        ingested_db, query="patient care guideline standard of care",
        requester_group="engineering", domain_filter="clinical",
    )

    assert result.total_candidates > 0  # clinical chunks do exist in the corpus
    assert result.scored == []  # but "engineering" is not in clinical's allowed_groups
    assert result.excluded_by_acl == result.total_candidates


def test_requester_group_with_clinical_access_gets_clinical_results(ingested_db):
    service = get_retrieval_service()

    result = service.search(
        ingested_db, query="patient care guideline standard of care",
        requester_group="clinical", domain_filter="clinical",
    )

    assert result.total_candidates > 0
    assert result.excluded_by_acl == 0
    assert len(result.scored) > 0
    assert all(sc.chunk.domain == "clinical" for sc in result.scored)


def test_executive_group_can_access_every_domain(ingested_db):
    # "executive" is in every domain's default_allowed_groups in the
    # controlled ontology yaml -- a cross-domain super-reader role.
    service = get_retrieval_service()
    for domain in ("clinical", "legal", "financial", "technical", "administrative"):
        result = service.search(ingested_db, query="policy", requester_group="executive", domain_filter=domain)
        assert result.excluded_by_acl == 0, f"executive unexpectedly excluded from domain={domain}"


def test_domain_filter_narrows_results_to_only_that_domain(ingested_db):
    service = get_retrieval_service()

    result = service.search(
        ingested_db, query="architecture design system", requester_group="executive", domain_filter="technical",
    )

    assert len(result.scored) > 0
    assert all(sc.chunk.domain == "technical" for sc in result.scored)


def test_domain_filter_excludes_other_domains_from_candidate_pool(ingested_db):
    service = get_retrieval_service()

    unfiltered = service.search(ingested_db, query="policy", requester_group="executive")
    filtered = service.search(ingested_db, query="policy", requester_group="executive", domain_filter="financial")

    assert filtered.total_candidates <= unfiltered.total_candidates
    assert all(sc.chunk.domain == "financial" for sc in filtered.scored)


def test_search_with_no_permitted_chunks_returns_empty_result_not_an_error(ingested_db):
    service = get_retrieval_service()
    # "finance" has no access to the clinical domain at all.
    result = service.search(ingested_db, query="diabetes care", requester_group="finance", domain_filter="clinical")
    assert result.scored == []
    assert result.latency_ms >= 0
