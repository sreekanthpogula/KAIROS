from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.document import Document
from app.retrieval.rag_factory import get_rag_service
from app.schemas.rag import CitationOut, RAGQueryRequest, RAGQueryResponse
from app.schemas.search import QueryUnderstandingOut, ScoredChunkOut

router = APIRouter()


@router.post("/query", response_model=RAGQueryResponse)
def rag_query(request: RAGQueryRequest, db: Session = Depends(get_db)):
    service = get_rag_service()
    result = service.answer(
        db, request.query, requester_group=request.requester_group,
        domain_filter=request.domain_filter, document_type_filter=request.document_type_filter,
    )

    doc_ids = {s.chunk.document_id for s in result.retrieval.scored} if result.retrieval else set()
    documents = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}

    scored_results = [
        ScoredChunkOut(
            chunk_id=s.chunk.id, document_id=s.chunk.document_id,
            document_filename=documents[s.chunk.document_id].filename if s.chunk.document_id in documents else "unknown",
            text=s.chunk.text, section=s.chunk.section, page_start=s.chunk.page_start, page_end=s.chunk.page_end,
            document_type=s.chunk.document_type, domain=s.chunk.domain, ontology_path=s.chunk.ontology_path,
            security_level=s.chunk.security_level, semantic_score=s.semantic_score, lexical_score=s.lexical_score,
            ontology_score=s.ontology_score, metadata_score=s.metadata_score, final_score=s.final_score,
        )
        for s in (result.retrieval.scored if result.retrieval else [])
    ]

    understanding = result.retrieval.understanding if result.retrieval else None

    return RAGQueryResponse(
        query=result.query, answer=result.answer,
        citations=[CitationOut(**vars(c)) for c in result.citations],
        groundedness=result.groundedness, mode=result.mode,
        understanding=QueryUnderstandingOut(
            domain=understanding.domain if understanding else None,
            document_type=understanding.document_type if understanding else None,
            ontology_id=understanding.ontology_id if understanding else None,
            topics=understanding.topics if understanding else [],
            entities=understanding.entities if understanding else [],
        ),
        scored_results=scored_results,
        excluded_by_acl=result.retrieval.excluded_by_acl if result.retrieval else 0,
        latency_ms=round(result.retrieval.latency_ms, 2) if result.retrieval else 0.0,
    )
