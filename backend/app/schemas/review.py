from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReviewTaskOut(BaseModel):
    id: str
    document_id: str
    document_filename: str
    status: str
    reason: str
    original_prediction: dict
    human_correction: dict | None = None
    reviewer: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class ReviewCorrectRequest(BaseModel):
    ontology_id: str
    reviewer: str = "demo-reviewer"
    notes: str | None = None


class ReviewApproveRequest(BaseModel):
    reviewer: str = "demo-reviewer"
    notes: str | None = None
