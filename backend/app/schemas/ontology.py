from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class OntologyMapping(BaseModel):
    """Exact shape from spec section 15."""

    ontology_id: str
    ontology_path: list[str]
    ontology_version: str


class OntologyTreeNode(BaseModel):
    id: str
    name: str
    level: str  # domain|category|type
    path: list[str]
    document_count: int = 0
    chunk_count: int = 0
    children: list["OntologyTreeNode"] = []


class OntologyNodeStats(BaseModel):
    id: str
    name: str
    level: str
    path: list[str]
    document_count: int
    chunk_count: int
    top_entities: list[dict]
    top_topics: list[dict]
    recent_documents: list[dict]
