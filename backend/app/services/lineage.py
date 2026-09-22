"""Builds the source -> document -> segment -> chunk lineage graph (spec
section 21). The RAG answer's citations already carry chunk_id/document_id;
the frontend calls this endpoint to render the full traceability chain
behind any citation."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.segment import DocumentSegment
from app.schemas.lineage import LineageEdge, LineageNode, LineageResponse


class LineageService:
    def build(self, db: Session, document_id: str) -> LineageResponse | None:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return None

        nodes: list[LineageNode] = []
        edges: list[LineageEdge] = []

        source_id = f"source:{doc.id}"
        nodes.append(
            LineageNode(
                id=source_id, type="source", label=doc.original_filename,
                metadata={"checksum": doc.checksum, "mime_type": doc.mime_type, "size_bytes": doc.size_bytes, "source_system": doc.source_system},
            )
        )

        doc_node_id = f"document:{doc.id}"
        nodes.append(
            LineageNode(
                id=doc_node_id, type="document", label=doc.filename,
                metadata={
                    "document_type": doc.document_type, "domain": doc.domain,
                    "ontology_path": " / ".join(doc.ontology_path) if doc.ontology_path else None,
                    "confidence": doc.classification_confidence, "security_level": doc.security_level,
                },
            )
        )
        edges.append(LineageEdge(source=source_id, target=doc_node_id))

        segments = db.query(DocumentSegment).filter(DocumentSegment.document_id == document_id).order_by(DocumentSegment.order_index).all()
        for seg in segments:
            seg_node_id = f"segment:{seg.id}"
            nodes.append(
                LineageNode(
                    id=seg_node_id, type="segment", label=seg.title or seg.segment_type,
                    metadata={"segment_type": seg.segment_type, "page_start": seg.page_start, "page_end": seg.page_end},
                )
            )
            parent_node_id = f"segment:{seg.parent_segment_id}" if seg.parent_segment_id else doc_node_id
            edges.append(LineageEdge(source=parent_node_id, target=seg_node_id))

        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
        for chunk in chunks:
            chunk_node_id = f"chunk:{chunk.id}"
            nodes.append(
                LineageNode(
                    id=chunk_node_id, type="chunk", label=f"Chunk {chunk.chunk_index}",
                    metadata={"text_preview": chunk.text[:160], "chunker_type": chunk.chunker_type, "page_start": chunk.page_start, "page_end": chunk.page_end},
                )
            )
            parent_node_id = f"segment:{chunk.segment_id}" if chunk.segment_id else doc_node_id
            edges.append(LineageEdge(source=parent_node_id, target=chunk_node_id))

        return LineageResponse(document_id=document_id, nodes=nodes, edges=edges)


def get_lineage_service() -> LineageService:
    return LineageService()
