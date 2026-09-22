"""Hybrid retrieval orchestration (spec section 24):

query -> query understanding -> metadata/ontology filters -> ACL filter ->
vector retrieval -> lexical retrieval -> fusion/rerank -> final context
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.embeddings.service import EmbeddingService
from app.models.chunk import Chunk
from app.retrieval.lexical_index import LexicalIndexService
from app.retrieval.query_understanding import QueryUnderstanding, QueryUnderstandingService
from app.retrieval.reranker import Reranker, ScoredChunk
from app.retrieval.vector_index import VectorIndexBackend


class RetrievalResult:
    def __init__(self, scored: list[ScoredChunk], understanding: QueryUnderstanding, total_candidates: int, excluded_by_acl: int, latency_ms: float):
        self.scored = scored
        self.understanding = understanding
        self.total_candidates = total_candidates
        self.excluded_by_acl = excluded_by_acl
        self.latency_ms = latency_ms


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_index: VectorIndexBackend,
        lexical_index: LexicalIndexService,
        query_understanding: QueryUnderstandingService,
        reranker: Reranker,
        settings: Settings,
    ):
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.lexical_index = lexical_index
        self.query_understanding = query_understanding
        self.reranker = reranker
        self.settings = settings

    def search(
        self,
        db: Session,
        query: str,
        requester_group: str = "employee",
        domain_filter: str | None = None,
        document_type_filter: str | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        t0 = time.perf_counter()
        top_k = top_k or self.settings.retrieval_top_k
        understanding = self.query_understanding.understand(query)

        base_query = db.query(Chunk)
        if domain_filter:
            base_query = base_query.filter(Chunk.domain == domain_filter)
        if document_type_filter:
            base_query = base_query.filter(Chunk.document_type == document_type_filter)

        candidates = base_query.all()
        total_candidates = len(candidates)

        allowed = [c for c in candidates if self._is_allowed(c, requester_group)]
        excluded_by_acl = total_candidates - len(allowed)
        allowed_ids = {c.id for c in allowed}

        if not allowed_ids:
            return RetrievalResult([], understanding, total_candidates, excluded_by_acl, (time.perf_counter() - t0) * 1000)

        query_vector = self.embedding_service.embed_text(query)
        semantic_scores = self.vector_index.semantic_search(db, query_vector, allowed_ids)
        lexical_scores = self.lexical_index.search(db, query, allowed_ids)

        chunk_by_id = {c.id: c for c in allowed}
        scored = [
            self.reranker.score(chunk_by_id[cid], semantic_scores.get(cid, 0.0), lexical_scores.get(cid, 0.0), understanding)
            for cid in allowed_ids
        ]
        scored.sort(key=lambda s: s.final_score, reverse=True)

        latency_ms = (time.perf_counter() - t0) * 1000
        return RetrievalResult(scored[:top_k], understanding, total_candidates, excluded_by_acl, latency_ms)

    @staticmethod
    def _is_allowed(chunk: Chunk, requester_group: str) -> bool:
        allowed_groups = chunk.allowed_groups or []
        if not allowed_groups:
            return True
        return requester_group in allowed_groups
