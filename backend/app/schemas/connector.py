from __future__ import annotations

from pydantic import BaseModel


class ConnectorCatalogEntry(BaseModel):
    type: str
    display_name: str
    description: str
    direction: str
    config_schema: dict


class ConnectorTestRequest(BaseModel):
    config: dict


class ConnectorTestResponse(BaseModel):
    ok: bool
    message: str


class ConnectorRunRequest(BaseModel):
    config: dict


class ConnectorRunResponse(BaseModel):
    job_id: str
    status: str
    total_documents: int
    completed_documents: int
    review_documents: int
    failed_documents: int
    duplicate_documents: int
