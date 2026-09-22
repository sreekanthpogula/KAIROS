from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.entity import Entity
from app.ontology.service import get_ontology_service
from app.schemas.ontology import OntologyNodeStats

router = APIRouter()


def _node_filter(model_ontology_col, node_id: str):
    return or_(model_ontology_col == node_id, model_ontology_col.like(f"{node_id}.%"))


def _annotate(node: dict, db: Session) -> dict:
    node["document_count"] = db.query(Document).filter(_node_filter(Document.ontology_id, node["id"])).count()
    node["chunk_count"] = db.query(Chunk).filter(_node_filter(Chunk.ontology_id, node["id"])).count()
    for child in node.get("children", []):
        _annotate(child, db)
    return node


@router.get("")
def get_ontology_tree(db: Session = Depends(get_db)):
    tree = get_ontology_service().build_tree()
    for domain in tree["children"]:
        _annotate(domain, db)
    tree["document_count"] = sum(d["document_count"] for d in tree["children"])
    tree["chunk_count"] = sum(d["chunk_count"] for d in tree["children"])
    return tree


@router.get("/{node_id}", response_model=OntologyNodeStats)
def get_ontology_node(node_id: str, db: Session = Depends(get_db)):
    ontology = get_ontology_service()
    node = ontology.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Ontology node not found")

    documents = db.query(Document).filter(_node_filter(Document.ontology_id, node_id)).order_by(Document.created_at.desc()).all()
    chunk_count = db.query(Chunk).filter(_node_filter(Chunk.ontology_id, node_id)).count()

    doc_ids = [d.id for d in documents]
    entities = db.query(Entity).filter(Entity.document_id.in_(doc_ids)).all() if doc_ids else []
    entity_counts = Counter(e.normalized_value for e in entities)

    topic_counts: Counter = Counter()
    if doc_ids:
        for chunk in db.query(Chunk).filter(Chunk.document_id.in_(doc_ids)).all():
            topic_counts.update(chunk.topics or [])

    return OntologyNodeStats(
        id=node.id, name=node.name, level=node.level, path=node.path,
        document_count=len(documents), chunk_count=chunk_count,
        top_entities=[{"value": v, "count": c} for v, c in entity_counts.most_common(8)],
        top_topics=[{"topic": t, "count": c} for t, c in topic_counts.most_common(8)],
        recent_documents=[{"id": d.id, "filename": d.filename, "confidence": d.classification_confidence, "status": d.status} for d in documents[:10]],
    )
