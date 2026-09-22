from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OntologyNode(Base):
    """Materialized view of the controlled ontology (loaded from
    ontology/healthcare_ontology.yaml at startup). Classifiers may only
    resolve to a leaf node that exists in this table — see ADR-001."""

    __tablename__ = "ontology_nodes"

    id: Mapped[str] = mapped_column(String(256), primary_key=True)  # e.g. legal.contract.provider_agreement
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(256), ForeignKey("ontology_nodes.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(128))
    level: Mapped[str] = mapped_column(String(32))  # domain|category|type
    path: Mapped[list] = mapped_column(JSON)  # ["Healthcare","Legal","Contracts","Provider Agreement"]
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ontology_version: Mapped[str] = mapped_column(String(16), default="1.0")
    depth: Mapped[int] = mapped_column(Integer, default=0)
