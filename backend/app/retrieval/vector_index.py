"""Semantic (vector) retrieval backend (spec section 23-24).

POC default is a numpy backend: load candidate chunks' embeddings and
compute cosine similarity in-process. This is the "do not pretend to
process 1TB locally" trade-off made explicit — it is correct and fast
enough for the POC's dozens-to-hundreds of chunks, and is swapped for
native pgvector ANN search (HNSW/IVFFlat index, `<=>` operator) at
production scale without any change to RetrievalService — see
docs/decisions.md and docs/scaling.md.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.embeddings.similarity import cosine_similarity_matrix
from app.models.embedding import Embedding


class VectorIndexBackend(ABC):
    @abstractmethod
    def semantic_search(self, db: Session, query_vector: list[float], candidate_chunk_ids: set[str]) -> dict[str, float]: ...


class NumpyVectorIndexBackend(VectorIndexBackend):
    """POC backend. Loads embeddings for the candidate set (already
    narrowed by ACL + explicit filters) and ranks by cosine similarity."""

    def semantic_search(self, db: Session, query_vector: list[float], candidate_chunk_ids: set[str]) -> dict[str, float]:
        if not candidate_chunk_ids:
            return {}
        rows = db.query(Embedding).filter(Embedding.chunk_id.in_(candidate_chunk_ids)).all()
        if not rows:
            return {}
        sims = cosine_similarity_matrix(query_vector, [r.vector for r in rows])
        return {row.chunk_id: max(0.0, sim) for row, sim in zip(rows, sims)}


def get_vector_index_backend() -> VectorIndexBackend:
    # VECTOR_BACKEND=pgvector is the designed production extension point
    # (native `vector` column + ANN index via app/embeddings — see
    # docs/decisions.md) but requires a real Postgres+pgvector instance to
    # exercise, which this local POC environment does not provision by
    # default. The numpy backend is what's actually tested end-to-end here.
    return NumpyVectorIndexBackend()
