"""Shared pytest fixtures for the ECIP backend test suite.

CRITICAL ordering constraint: DATABASE_URL must be set in the environment
BEFORE any `app.*` module is ever imported in this process, because
app/core/config.py's get_settings() is @lru_cache'd (built once, from the
environment, at first call) and app/core/db.py builds its SQLAlchemy engine
at MODULE IMPORT TIME from get_settings(). Because conftest.py is always
collected by pytest before any test module is imported, doing this here,
before any other import, guarantees every test in the suite talks to the
same isolated on-disk SQLite test database instead of the real
data/ecip.db used by the manually-verified running backend.
"""
from __future__ import annotations

import os
from pathlib import Path

_TEST_DB_PATH = Path(__file__).parent / "test_ecip.db"
os.environ.setdefault("DATABASE_URL", "sqlite:///" + _TEST_DB_PATH.as_posix())
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_MODE", "false")

import json  # noqa: E402
from typing import Iterator  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402

# Repo layout: backend/tests/conftest.py -> parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
GOLDEN_LABELS_PATH = SAMPLES_DIR / "golden_labels.json"


def read_sample_bytes(filename: str) -> bytes:
    """Reads a file from the synthetic sample corpus (data/samples/)."""
    return (SAMPLES_DIR / filename).read_bytes()


def load_golden_labels() -> list[dict]:
    with open(GOLDEN_LABELS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _register_all_models() -> None:
    """Imports every model module so its class is registered on
    Base.metadata before create_all/drop_all — mirrors app.core.db.init_db,
    plus retrieval_log which init_db also imports."""
    from app.models import (  # noqa: F401
        chunk,
        classification_result,
        document,
        embedding,
        entity,
        ingestion_job,
        ontology_node,
        processing_event,
        retrieval_log,
        review_task,
        segment,
    )


def reset_db() -> None:
    """Drops and recreates every table. Required instead of a
    transaction-rollback pattern because PipelineOrchestrator issues real,
    repeated db.commit() calls mid-pipeline — an outer rollback would not
    undo those."""
    _register_all_models()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db() -> Iterator[Session]:
    """Function-scoped clean database. Only tests that actually touch the
    DB should depend on this fixture — pure unit tests (file detection,
    ontology lookups, confidence math, chunker selection) don't need it and
    skip the reset cost."""
    reset_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def golden_labels() -> list[dict]:
    return load_golden_labels()


def sample_corpus_filenames() -> list[str]:
    """Every real document in the sample corpus (excludes the golden_labels
    manifest and any dotfiles like .gitkeep)."""
    return sorted(
        p.name for p in SAMPLES_DIR.iterdir()
        if p.is_file() and p.suffix != ".json" and not p.name.startswith(".")
    )


def ingest_sample_corpus(db: Session) -> list:
    """Ingests every real file in data/samples/ through the fully-wired
    pipeline orchestrator against the given (already-reset) db session.
    Returns the resulting Document rows, one per file, in filename order."""
    from app.pipeline.factory import get_pipeline_orchestrator

    orchestrator = get_pipeline_orchestrator(db)
    return [
        orchestrator.ingest_document(filename, read_sample_bytes(filename))
        for filename in sample_corpus_filenames()
    ]
