"""Grounded answer generation (spec section 27).

DEMO_MODE answers are extractive and fully deterministic: the sentence(s)
within the top retrieved chunks that best overlap the query's own words,
stitched together — no generative model involved, so the same query
always produces the same answer and every word is traceable to a specific
chunk. LLM_MODE swaps in an actual generative call over the same retrieved
context when a real key is configured. Either way, every answer carries
citations back to document/section/page (spec section 21 lineage).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.retrieval.reranker import ScoredChunk
from app.retrieval.service import RetrievalResult, RetrievalService
from app.services.llm_provider import BaseLLMProvider

_WORD_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "as", "by", "is", "are", "what", "how", "does", "do"}


@dataclass
class Citation:
    document_id: str
    document_filename: str
    section: str | None
    page_start: int | None
    page_end: int | None
    chunk_id: str
    final_score: float


@dataclass
class RAGAnswer:
    query: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    groundedness: str = "none"
    mode: str = "demo_deterministic"
    retrieval: RetrievalResult | None = None


def _tokenize(text: str) -> set[str]:
    return {t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS}


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text.replace("\n", " ")) if s.strip()]


def _best_sentences(text: str, query_tokens: set[str], max_sentences: int) -> list[str]:
    scored = []
    for sentence in _split_sentences(text):
        overlap = len(_tokenize(sentence) & query_tokens)
        if overlap:
            scored.append((overlap, sentence))
    scored.sort(key=lambda p: p[0], reverse=True)
    if scored:
        return [s for _, s in scored[:max_sentences]]
    sentences = _split_sentences(text)
    return sentences[:1]


class RAGService:
    NO_ANSWER_TEXT = "No documents you have access to contain information relevant to this question."
    # Below this final_score, a "top match" is more coincidence than
    # relevance (e.g. all genuinely relevant documents were excluded by
    # ACL, leaving only weak leftover matches) — answer honestly instead
    # of confidently synthesizing from noise.
    MIN_RELEVANT_SCORE = 0.30

    def __init__(self, retrieval_service: RetrievalService, llm_provider: BaseLLMProvider, settings: Settings):
        self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider
        self.settings = settings

    def answer(
        self,
        db: Session,
        query: str,
        requester_group: str = "employee",
        domain_filter: str | None = None,
        document_type_filter: str | None = None,
    ) -> RAGAnswer:
        retrieval = self.retrieval_service.search(db, query, requester_group, domain_filter, document_type_filter, top_k=5)

        relevant = [s for s in retrieval.scored if s.final_score >= self.MIN_RELEVANT_SCORE]
        if not relevant:
            reason = (
                " (some documents were excluded because they are outside your access level)"
                if retrieval.excluded_by_acl
                else ""
            )
            return RAGAnswer(query=query, answer=self.NO_ANSWER_TEXT + reason, citations=[], groundedness="none", retrieval=retrieval)

        top = relevant[:3]
        documents = {
            d.id: d for d in db.query(Document).filter(Document.id.in_({s.chunk.document_id for s in top})).all()
        }

        if self.settings.effective_llm_mode:
            answer_text, mode = self._llm_answer(query, top, documents), "llm"
        else:
            answer_text, mode = self._deterministic_answer(query, top), "demo_deterministic"

        citations = [self._citation(s, documents) for s in top]
        groundedness = self._groundedness(top)

        return RAGAnswer(query=query, answer=answer_text, citations=citations, groundedness=groundedness, mode=mode, retrieval=retrieval)

    # ------------------------------------------------------------------ #
    def _deterministic_answer(self, query: str, top: list[ScoredChunk]) -> str:
        query_tokens = _tokenize(query)
        parts: list[str] = []
        for scored in top:
            parts.extend(_best_sentences(scored.chunk.text, query_tokens, max_sentences=2 if scored is top[0] else 1))

        seen: set[str] = set()
        unique = [p for p in parts if not (p in seen or seen.add(p))]
        if not unique:
            return "The retrieved documents did not contain a statement directly matching this question."
        return " ".join(unique[:4])

    def _llm_answer(self, query: str, top: list[ScoredChunk], documents: dict[str, Document]) -> str:
        context = "\n\n".join(
            f"[{i + 1}] ({documents[s.chunk.document_id].filename}, {s.chunk.section or 'n/a'}): {s.chunk.text}"
            for i, s in enumerate(top)
        )
        system = (
            "You are an enterprise knowledge assistant. Answer strictly using the provided context. "
            "Cite sources inline using [n] matching the numbered context blocks. If the context does not "
            "answer the question, say so plainly."
        )
        user = f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"
        return self.llm_provider.complete(system, user, max_tokens=400)

    @staticmethod
    def _citation(scored: ScoredChunk, documents: dict[str, Document]) -> Citation:
        doc = documents.get(scored.chunk.document_id)
        return Citation(
            document_id=scored.chunk.document_id,
            document_filename=doc.filename if doc else "unknown",
            section=scored.chunk.section,
            page_start=scored.chunk.page_start,
            page_end=scored.chunk.page_end,
            chunk_id=scored.chunk.id,
            final_score=scored.final_score,
        )

    @staticmethod
    def _groundedness(top: list[ScoredChunk]) -> str:
        # Calibrated to this POC's actual score scale (see
        # LexicalIndexService/Reranker docstrings for why: local_hash
        # embeddings and a neutral 0.5 ontology default cap "final_score"
        # well below 1.0 even for a perfect match) rather than an
        # arbitrary 0-1 scale. Anything below MIN_RELEVANT_SCORE never
        # reaches here at all (see `answer()`).
        if not top:
            return "none"
        best = top[0].final_score
        if best >= 0.45:
            return "high"
        if best >= RAGService.MIN_RELEVANT_SCORE:
            return "medium"
        return "low"
