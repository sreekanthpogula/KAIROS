"""Deterministic query understanding (spec section 25).

Reuses RuleBasedClassifier against the query text itself — the same
controlled-ontology keyword signals that decide what a document *is* also
decide what a query is *about*. If nothing matches with reasonable
confidence, domain/document_type stay None and retrieval falls back to
pure semantic+lexical ranking rather than forcing a wrong filter.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.classifiers.base import ClassifierInput
from app.classifiers.rule_based import RuleBasedClassifier
from app.ontology.service import OntologyService
from app.services.entity_extractor import BaseEntityExtractor
from app.services.topic_extractor import extract_topics

MIN_DOMAIN_CONFIDENCE = 0.15  # queries are short, so raw keyword-hit scores
# are structurally much smaller than a full document's — a single decisive
# keyword ("termination") should be enough to set a soft domain hint for
# reranking. This never hard-filters results (see Reranker._ontology_score),
# so a low bar here costs little even when it's wrong.


@dataclass
class QueryUnderstanding:
    raw_query: str
    domain: str | None
    document_type: str | None
    ontology_id: str | None
    topics: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)


class QueryUnderstandingService:
    def __init__(self, rule_classifier: RuleBasedClassifier, ontology: OntologyService, entity_extractor: BaseEntityExtractor):
        self.rule_classifier = rule_classifier
        self.ontology = ontology
        self.entity_extractor = entity_extractor

    def understand(self, query: str) -> QueryUnderstanding:
        vote = self.rule_classifier.classify(
            ClassifierInput(filename="", mime_type="", parser_type="text", full_text=query, headings=[])
        )

        domain = document_type = ontology_id = None
        if vote.ontology_id and vote.confidence >= MIN_DOMAIN_CONFIDENCE:
            ontology_id = vote.ontology_id
            domain_node = self.ontology.domain_of(ontology_id)
            domain = domain_node.id if domain_node else None
            document_type = self.ontology.document_type_for(ontology_id)

        return QueryUnderstanding(
            raw_query=query,
            domain=domain,
            document_type=document_type,
            ontology_id=ontology_id,
            topics=extract_topics(query, max_topics=4),
            entities=[e.value for e in self.entity_extractor.extract(query)],
        )
