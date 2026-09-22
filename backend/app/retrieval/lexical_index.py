"""Lexical (BM25-style) retrieval (spec section 24 — "do not pretend
vector search alone is sufficient"). Rebuilds a BM25 index over the
candidate set per query, which is a deliberate POC simplification —
fine at dozens-to-hundreds of chunks, but a production system would
maintain a persistent inverted index (Postgres tsvector/GIN, or a real
search engine) rather than rebuild on every request. See docs/retrieval.md.
"""
from __future__ import annotations

import math
import re

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models.chunk import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "as", "by", "is",
    "are", "this", "that", "shall", "will", "at", "from", "any", "may", "not", "it", "what",
    "how", "does", "do", "be",
}

# Saturating transform on the RAW BM25 score rather than min-max scaling
# against whatever candidate set happens to be in play. This matters once
# ACL filtering narrows the pool to e.g. 15 unrelated documents: min-max
# normalization would inflate the best-of-a-bad-lot match to a false 1.0,
# while this absolute scale correctly reports it as still weak. K=6 is
# calibrated so a genuine multi-keyword match (raw ~6-8) lands ~0.6-0.75,
# and a coincidental single-stopword overlap (raw ~0-1) stays near 0.
BM25_SATURATION_K = 6.0


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class LexicalIndexService:
    def search(self, db: Session, query: str, candidate_chunk_ids: set[str]) -> dict[str, float]:
        if not candidate_chunk_ids:
            return {}
        rows = db.query(Chunk.id, Chunk.text).filter(Chunk.id.in_(candidate_chunk_ids)).all()
        if not rows:
            return {}

        corpus_ids = [r.id for r in rows]
        bm25 = BM25Okapi([_tokenize(r.text) for r in rows])
        raw_scores = bm25.get_scores(_tokenize(query))

        return {cid: 1.0 - math.exp(-max(0.0, float(score)) / BM25_SATURATION_K) for cid, score in zip(corpus_ids, raw_scores)}
