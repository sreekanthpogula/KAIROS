from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.scale_simulator import SCALE_PRESETS, DEFAULT_WORKER_COUNT, resolve_document_count, simulate

router = APIRouter()


@router.get("/presets")
def get_presets():
    return {"document_count_presets": SCALE_PRESETS, "default_worker_count": DEFAULT_WORKER_COUNT}


@router.get("")
def run_simulation(document_count: str = "15", worker_count: int = DEFAULT_WORKER_COUNT, db: Session = Depends(get_db)):
    return simulate(db, resolve_document_count(document_count), worker_count)
