"""Loads and serves the controlled enterprise ontology.

This is the ONLY place ontology structure is read from disk. Every other
module (classifiers, chunker selector, security defaults, API routes) goes
through this service, so the ontology can be edited/versioned in
ontology/healthcare_ontology.yaml without touching application code
(ADR-001, docs/decisions.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from app.core.config import get_settings


@dataclass
class OntologyNode:
    id: str
    name: str
    level: str  # domain | category | type
    path: list[str]
    parent_id: str | None = None
    keywords: list[str] = field(default_factory=list)
    chunker: str | None = None
    document_type: str | None = None
    default_security_level: str | None = None
    default_allowed_groups: list[str] = field(default_factory=list)


class OntologyService:
    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path
        self.version: str = "1.0"
        self.root_name: str = "Healthcare"
        self._nodes: dict[str, OntologyNode] = {}
        self._children: dict[str, list[str]] = {}
        self._load()

    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        with open(self.yaml_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        self.version = str(raw.get("ontology_version", "1.0"))
        self.root_name = raw.get("root", "Healthcare")

        for domain in raw.get("domains", []):
            domain_node = OntologyNode(
                id=domain["id"],
                name=domain["name"],
                level="domain",
                path=[self.root_name, domain["name"]],
                parent_id=None,
                default_security_level=domain.get("default_security_level", "internal"),
                default_allowed_groups=list(domain.get("default_allowed_groups", [])),
            )
            self._register(domain_node)

            for category in domain.get("categories", []):
                category_node = OntologyNode(
                    id=category["id"],
                    name=category["name"],
                    level="category",
                    path=domain_node.path + [category["name"]],
                    parent_id=domain_node.id,
                    chunker=category.get("chunker", "generic"),
                    default_security_level=domain_node.default_security_level,
                    default_allowed_groups=domain_node.default_allowed_groups,
                )
                self._register(category_node)

                for type_ in category.get("types", []):
                    type_node = OntologyNode(
                        id=type_["id"],
                        name=type_["name"],
                        level="type",
                        path=category_node.path + [type_["name"]],
                        parent_id=category_node.id,
                        keywords=[k.lower() for k in type_.get("keywords", [])],
                        chunker=category_node.chunker,
                        document_type=type_.get("document_type", type_["id"].split(".")[-1]),
                        default_security_level=category_node.default_security_level,
                        default_allowed_groups=category_node.default_allowed_groups,
                    )
                    self._register(type_node)

    def _register(self, node: OntologyNode) -> None:
        self._nodes[node.id] = node
        if node.parent_id:
            self._children.setdefault(node.parent_id, []).append(node.id)

    # ------------------------------------------------------------------ #
    def get(self, ontology_id: str) -> OntologyNode | None:
        return self._nodes.get(ontology_id)

    def exists(self, ontology_id: str) -> bool:
        return ontology_id in self._nodes

    def is_leaf(self, ontology_id: str) -> bool:
        node = self._nodes.get(ontology_id)
        return bool(node) and node.level == "type"

    def all_nodes(self) -> list[OntologyNode]:
        return list(self._nodes.values())

    def all_types(self) -> list[OntologyNode]:
        return [n for n in self._nodes.values() if n.level == "type"]

    def all_domains(self) -> list[OntologyNode]:
        return [n for n in self._nodes.values() if n.level == "domain"]

    def children_of(self, ontology_id: str) -> list[OntologyNode]:
        return [self._nodes[cid] for cid in self._children.get(ontology_id, [])]

    def path_for(self, ontology_id: str) -> list[str]:
        node = self._nodes.get(ontology_id)
        return node.path if node else []

    def domain_of(self, ontology_id: str) -> OntologyNode | None:
        node = self._nodes.get(ontology_id)
        while node and node.level != "domain":
            node = self._nodes.get(node.parent_id) if node.parent_id else None
        return node

    def document_type_for(self, ontology_id: str) -> str | None:
        node = self._nodes.get(ontology_id)
        return node.document_type if node else None

    def document_subtype_for(self, ontology_id: str) -> str | None:
        node = self._nodes.get(ontology_id)
        if not node:
            return None
        return node.id.split(".")[-1]

    def chunker_for(self, ontology_id: str) -> str:
        node = self._nodes.get(ontology_id)
        return node.chunker if node and node.chunker else "generic"

    def security_defaults_for(self, ontology_id: str) -> tuple[str, list[str]]:
        node = self._nodes.get(ontology_id)
        if not node:
            settings = get_settings()
            return settings.default_security_level, ["employee"]
        return node.default_security_level or "internal", list(node.default_allowed_groups) or ["employee"]

    def resolve_or_none(self, ontology_id: str) -> OntologyNode | None:
        """Enforces controlled classification (spec section 13): a
        classifier may only resolve to a type id that exists in this
        ontology. Anything else must be treated as unknown by the caller
        (mapped to a nearest neighbor, or routed to REVIEW_REQUIRED)."""
        node = self._nodes.get(ontology_id)
        return node if node and node.level == "type" else None

    def build_tree(self) -> dict:
        def node_dict(node: OntologyNode) -> dict:
            return {
                "id": node.id,
                "name": node.name,
                "level": node.level,
                "path": node.path,
                "children": [node_dict(self._nodes[c]) for c in self._children.get(node.id, [])],
            }

        return {
            "id": "root",
            "name": self.root_name,
            "level": "root",
            "path": [self.root_name],
            "children": [node_dict(d) for d in self.all_domains()],
        }


@lru_cache
def get_ontology_service() -> OntologyService:
    settings = get_settings()
    return OntologyService(settings.ontology_path)
