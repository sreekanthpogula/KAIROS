from __future__ import annotations

from functools import lru_cache

from app.classifiers.rule_based import RuleBasedClassifier
from app.core.config import get_settings
from app.embeddings.service import get_embedding_service
from app.ontology.service import get_ontology_service
from app.retrieval.lexical_index import LexicalIndexService
from app.retrieval.query_understanding import QueryUnderstandingService
from app.retrieval.reranker import Reranker
from app.retrieval.service import RetrievalService
from app.retrieval.vector_index import get_vector_index_backend
from app.services.entity_extractor import get_entity_extractor


@lru_cache
def get_retrieval_service() -> RetrievalService:
    settings = get_settings()
    ontology = get_ontology_service()
    return RetrievalService(
        embedding_service=get_embedding_service(),
        vector_index=get_vector_index_backend(),
        lexical_index=LexicalIndexService(),
        query_understanding=QueryUnderstandingService(RuleBasedClassifier(ontology), ontology, get_entity_extractor()),
        reranker=Reranker(settings),
        settings=settings,
    )
