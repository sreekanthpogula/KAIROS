from __future__ import annotations

from pydantic import BaseModel


class LineageNode(BaseModel):
    id: str
    type: str  # source | document | segment | chunk
    label: str
    metadata: dict = {}


class LineageEdge(BaseModel):
    source: str
    target: str


class LineageResponse(BaseModel):
    document_id: str
    nodes: list[LineageNode]
    edges: list[LineageEdge]
