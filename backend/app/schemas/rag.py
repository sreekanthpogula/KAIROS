from __future__ import annotations

from pydantic import BaseModel

from app.schemas.search import QueryUnderstandingOut, ScoredChunkOut


class RAGQueryRequest(BaseModel):
    query: str
    requester_group: str = "employee"
    domain_filter: str | None = None
    document_type_filter: str | None = None


class CitationOut(BaseModel):
    document_id: str
    document_filename: str
    section: str | None
    page_start: int | None
    page_end: int | None
    chunk_id: str
    final_score: float


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationOut]
    groundedness: str
    mode: str
    understanding: QueryUnderstandingOut
    scored_results: list[ScoredChunkOut]
    excluded_by_acl: int
    latency_ms: float
