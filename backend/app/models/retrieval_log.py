from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import new_id
from app.models.document import utcnow


class RetrievalLog(Base):
    """Every search/RAG query, its understanding, filters, and the scored
    result set — powers retrieval explanation (section 45) and evaluation."""

    __tablename__ = "retrieval_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_text: Mapped[str] = mapped_column(Text)
    requester_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    query_understanding: Mapped[dict] = mapped_column(JSON, default=dict)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[list] = mapped_column(JSON, default=list)

    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(16), default="search")  # search|rag

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
