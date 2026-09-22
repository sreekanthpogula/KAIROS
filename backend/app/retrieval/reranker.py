"""Explainable reranking (spec sections 26 & 45).

A weighted-sum heuristic, explicitly labeled as a POC stand-in — the
interface is designed so a real cross-encoder/reranker model could
replace `Reranker.score()` without changing anything upstream (retrieval
still produces the same semantic/lexical candidate scores either way).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.models.chunk import Chunk
from app.retrieval.query_understanding import QueryUnderstanding


@dataclass
class ScoredChunk:
    chunk: Chunk
    semantic_score: float
    lexical_score: float
    ontology_score: float
    metadata_score: float
    final_score: float


class Reranker:
    def __init__(self, settings: Settings):
        self.w_semantic = settings.weight_semantic
        self.w_lexical = settings.weight_lexical
        self.w_ontology = settings.weight_ontology
        self.w_metadata = settings.weight_metadata

    def score(self, chunk: Chunk, semantic_score: float, lexical_score: float, understanding: QueryUnderstanding) -> ScoredChunk:
        ontology_score = self._ontology_score(chunk, understanding)
        metadata_score = self._metadata_score(chunk, understanding)
        final_score = (
            self.w_semantic * semantic_score
            + self.w_lexical * lexical_score
            + self.w_ontology * ontology_score
            + self.w_metadata * metadata_score
        )
        return ScoredChunk(
            chunk=chunk, semantic_score=round(semantic_score, 4), lexical_score=round(lexical_score, 4),
            ontology_score=round(ontology_score, 4), metadata_score=round(metadata_score, 4), final_score=round(final_score, 4),
        )

    @staticmethod
    def _ontology_score(chunk: Chunk, understanding: QueryUnderstanding) -> float:
        """No strong query hint -> neutral 0.5 rather than 0, so queries
        without a clear ontology signal aren't unfairly penalized."""
        parts, matched = 0, 0
        if understanding.domain:
            parts += 1
            matched += chunk.domain == understanding.domain
        if understanding.document_type:
            parts += 1
            matched += chunk.document_type == understanding.document_type
        return matched / parts if parts else 0.5

    @staticmethod
    def _metadata_score(chunk: Chunk, understanding: QueryUnderstanding) -> float:
        confidence = chunk.classification_confidence if chunk.classification_confidence is not None else 0.5
        signal_count = len(understanding.topics) + len(understanding.entities)
        if signal_count == 0:
            return confidence
        chunk_topics = set(chunk.topics or [])
        chunk_entities = {e.lower() for e in (chunk.entities or [])}
        overlap = len(chunk_topics & set(understanding.topics))
        overlap += sum(1 for e in understanding.entities if e.lower() in chunk_entities)
        overlap_ratio = overlap / signal_count
        return 0.7 * confidence + 0.3 * overlap_ratio
