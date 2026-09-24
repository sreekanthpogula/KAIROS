from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import connectors, documents, health, ingestion, metrics, ontology, rag, reviews, scale, search
from app.core import runtime_state
from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.core.startup import sync_ontology_nodes
from app.ontology.service import get_ontology_service

settings = get_settings()
logger = logging.getLogger("kcip.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        db = SessionLocal()
        try:
            sync_ontology_nodes(db, get_ontology_service())
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 - deliberately broad: startup must never take the whole API down
        runtime_state.startup_error = f"{type(exc).__name__}: {exc}"
        logger.error("KCIP startup failed - API is running in a degraded state: %s", runtime_state.startup_error, exc_info=True)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(ontology.router, prefix="/api/ontology", tags=["ontology"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(scale.router, prefix="/api/scale-simulator", tags=["scale-simulator"])
app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])
