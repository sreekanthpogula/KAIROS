"""Central application configuration.

Every environment-dependent decision (mock vs. LLM mode, storage backend,
embedding provider, confidence thresholds, rerank weights) is read from here
so that no module hard-codes a provider or a business threshold.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise Content Intelligence Platform"
    app_short_name: str = "ECIP"
    environment: str = "local"

    # --- Mode switches -----------------------------------------------
    # DEMO_MODE runs the entire pipeline deterministically with no external
    # API calls. LLM_MODE is only honored for stages that explicitly support
    # an LLM-backed provider (ambiguous-case classification, RAG answer
    # synthesis) and only when an API key is actually configured.
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    llm_mode: bool = Field(default=False, alias="LLM_MODE")

    # --- Storage -------------------------------------------------------
    # Production target is PostgreSQL + pgvector (see docker-compose.yml).
    # Default here is a zero-setup SQLite file so the POC runs with no
    # external services. The DB/vector layers are abstracted behind
    # interfaces precisely so this swap does not touch business logic.
    database_url: str = Field(default=f"sqlite:///{(REPO_ROOT / 'data' / 'ecip.db').as_posix()}", alias="DATABASE_URL")
    vector_backend: Literal["numpy", "pgvector"] = Field(default="numpy", alias="VECTOR_BACKEND")

    @field_validator("database_url", mode="after")
    @classmethod
    def _normalize_postgres_scheme(cls, value: str) -> str:
        """Neon/Heroku/Railway all hand out `postgres://` or bare
        `postgresql://` connection strings. SQLAlchemy 2.x needs an explicit
        driver (`+psycopg`) — without this, pasting a provider's connection
        string as-is fails with a confusing "can't load plugin" error."""
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    # --- Embeddings ------------------------------------------------------
    embedding_provider: Literal["local_hash", "sentence_transformers", "openai_compatible"] = Field(
        default="local_hash", alias="EMBEDDING_PROVIDER"
    )
    embedding_dim: int = Field(default=384, alias="EMBEDDING_DIM")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    # --- LLM (provider-independent; OpenAI-compatible wire format) ------
    llm_provider: Literal["mock", "openai_compatible"] = Field(default="mock", alias="LLM_PROVIDER")
    llm_api_base: str = Field(default="https://api.openai.com/v1", alias="LLM_API_BASE")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")

    # --- OCR (pluggable, optional) ---------------------------------------
    ocr_provider: Literal["none", "tesseract"] = Field(default="none", alias="OCR_PROVIDER")

    # --- Ontology --------------------------------------------------------
    # Lives inside backend/app/ (not a REPO_ROOT-relative sibling) on
    # purpose: serverless platforms (Vercel) that deploy `backend/` as a
    # standalone function bundle don't include sibling directories from
    # the repo root unless a platform-specific "include outside root
    # files" setting is enabled. Keeping this self-contained means the
    # backend works correctly regardless of that setting.
    ontology_path: str = Field(
        default=str(BACKEND_DIR / "app" / "ontology_data" / "healthcare_ontology.yaml"), alias="ONTOLOGY_PATH"
    )
    ontology_version: str = Field(default="1.0", alias="ONTOLOGY_VERSION")

    # --- Component versions (persisted onto every record for traceability)
    extractor_version: str = Field(default="1.0", alias="EXTRACTOR_VERSION")
    classifier_version: str = Field(default="1.2", alias="CLASSIFIER_VERSION")
    chunker_version: str = Field(default="1.1", alias="CHUNKER_VERSION")

    # --- Confidence routing ----------------------------------------------
    confidence_auto_accept: float = Field(default=0.90, alias="CONFIDENCE_AUTO_ACCEPT")
    confidence_secondary_validation: float = Field(default=0.70, alias="CONFIDENCE_SECONDARY_VALIDATION")

    # --- Hybrid retrieval / reranking weights (POC heuristic, tunable) ---
    weight_semantic: float = Field(default=0.45, alias="WEIGHT_SEMANTIC")
    weight_lexical: float = Field(default=0.25, alias="WEIGHT_LEXICAL")
    weight_ontology: float = Field(default=0.20, alias="WEIGHT_ONTOLOGY")
    weight_metadata: float = Field(default=0.10, alias="WEIGHT_METADATA")
    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")

    # --- Connector catalog ---------------------------------------------------
    # Shared secret for the webhook (push) connector — other systems POST
    # documents to /api/connectors/webhook/ingest with this as a bearer
    # token. Empty by default, which disables the endpoint entirely
    # (rather than accepting unauthenticated pushes) — set a real value
    # to turn it on.
    webhook_ingestion_token: str = Field(default="", alias="WEBHOOK_INGESTION_TOKEN")

    # --- Storage paths -----------------------------------------------------
    upload_dir: str = Field(default=str(REPO_ROOT / "data" / "raw"), alias="UPLOAD_DIR")
    processed_dir: str = Field(default=str(REPO_ROOT / "data" / "processed"), alias="PROCESSED_DIR")
    sample_dir: str = Field(default=str(REPO_ROOT / "data" / "samples"), alias="SAMPLE_DIR")

    # --- CORS --------------------------------------------------------------
    # Accepts a JSON array OR a plain comma-separated string (the latter is
    # far easier to paste into a Vercel/Render/Railway env var UI than JSON).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"], alias="CORS_ORIGINS"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value):
        # NoDecode above stops pydantic-settings from trying (and failing)
        # to JSON-parse this env var itself, so a plain comma-separated
        # string reaches this validator untouched.
        if isinstance(value, str):
            if value.strip().startswith("["):
                import json

                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # --- Security ------------------------------------------------------------
    default_security_level: str = Field(default="internal", alias="DEFAULT_SECURITY_LEVEL")
    available_groups: list[str] = Field(
        default_factory=lambda: [
            "employee",
            "legal",
            "provider-management",
            "finance",
            "clinical",
            "engineering",
            "executive",
        ]
    )

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def effective_llm_mode(self) -> bool:
        """LLM_MODE only takes effect if an API key is actually present."""
        return self.llm_mode and bool(self.llm_api_key) and self.llm_provider != "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
