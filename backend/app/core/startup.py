from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ontology_node import OntologyNode
from app.ontology.service import OntologyService


def sync_ontology_nodes(db: Session, ontology: OntologyService) -> None:
    """Materializes the YAML-defined ontology into the ontology_nodes
    table. Nodes are registered parent-before-child during OntologyService
    load, so a straight re-insert never violates the self-referential FK."""
    db.query(OntologyNode).delete()
    for node in ontology.all_nodes():
        db.add(
            OntologyNode(
                id=node.id, parent_id=node.parent_id, name=node.name, level=node.level,
                path=node.path, description=None, ontology_version=ontology.version, depth=len(node.path) - 1,
            )
        )
    db.commit()
