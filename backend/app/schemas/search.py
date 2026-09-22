from __future__ import annotations

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    requester_group: str = "employee"
    domain_filter: str | None = None
    document_type_filter: str | None = None
    top_k: int | None = None


class ScoredChunkOut(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    text: str
    section: str | None
    page_start: int | None
    page_end: int | None
    document_type: str | None
    domain: str | None
    ontology_path: str | None
    security_level: str
    semantic_score: float
    lexical_score: float
    ontology_score: float
    metadata_score: float
    final_score: float


class QueryUnderstandingOut(BaseModel):
    domain: str | None
    document_type: str | None
    ontology_id: str | None
    topics: list[str]
    entities: list[str]


class SearchResponse(BaseModel):
    query: str
    understanding: QueryUnderstandingOut
    results: list[ScoredChunkOut]
    total_candidates: int
    excluded_by_acl: int
    latency_ms: float
