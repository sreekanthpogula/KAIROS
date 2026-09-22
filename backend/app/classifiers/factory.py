from __future__ import annotations

from functools import lru_cache

from app.classifiers.embedding_based import EmbeddingClassifier
from app.classifiers.hybrid import HybridClassifier
from app.classifiers.llm_based import LLMClassifier
from app.classifiers.rule_based import RuleBasedClassifier
from app.core.config import get_settings
from app.embeddings.service import get_embedding_service
from app.ontology.service import get_ontology_service
from app.services.confidence import get_confidence_service
from app.services.llm_provider import get_llm_provider


@lru_cache
def get_hybrid_classifier() -> HybridClassifier:
    settings = get_settings()
    ontology = get_ontology_service()
    return HybridClassifier(
        rule_classifier=RuleBasedClassifier(ontology),
        embedding_classifier=EmbeddingClassifier(get_embedding_service(), ontology),
        llm_classifier=LLMClassifier(get_llm_provider(), ontology),
        ontology=ontology,
        confidence_service=get_confidence_service(),
        settings=settings,
    )
