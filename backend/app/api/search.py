from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.document import Document
from app.retrieval.factory import get_retrieval_service
from app.schemas.search import QueryUnderstandingOut, ScoredChunkOut, SearchRequest, SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, db: Session = Depends(get_db)):
    service = get_retrieval_service()
    result = service.search(
        db, request.query, requester_group=request.requester_group,
        domain_filter=request.domain_filter, document_type_filter=request.document_type_filter, top_k=request.top_k,
    )

    doc_ids = {s.chunk.document_id for s in result.scored}
    documents = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}

    results = [
        ScoredChunkOut(
            chunk_id=s.chunk.id, document_id=s.chunk.document_id,
            document_filename=documents[s.chunk.document_id].filename if s.chunk.document_id in documents else "unknown",
            text=s.chunk.text, section=s.chunk.section, page_start=s.chunk.page_start, page_end=s.chunk.page_end,
            document_type=s.chunk.document_type, domain=s.chunk.domain, ontology_path=s.chunk.ontology_path,
            security_level=s.chunk.security_level, semantic_score=s.semantic_score, lexical_score=s.lexical_score,
            ontology_score=s.ontology_score, metadata_score=s.metadata_score, final_score=s.final_score,
        )
        for s in result.scored
    ]

    return SearchResponse(
        query=request.query,
        understanding=QueryUnderstandingOut(
            domain=result.understanding.domain, document_type=result.understanding.document_type,
            ontology_id=result.understanding.ontology_id, topics=result.understanding.topics, entities=result.understanding.entities,
        ),
        results=results, total_candidates=result.total_candidates, excluded_by_acl=result.excluded_by_acl, latency_ms=round(result.latency_ms, 2),
    )
