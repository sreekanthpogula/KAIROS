from __future__ import annotations

from app.classifiers.base import BaseDocumentClassifier, ClassifierInput, ClassifierVote
from app.embeddings.service import EmbeddingService
from app.embeddings.similarity import cosine_similarity
from app.ontology.service import OntologyService


class EmbeddingClassifier(BaseDocumentClassifier):
    """Casts a semantic-similarity vote by comparing the document's
    embedding against a prototype embedding synthesized for every
    controlled ontology leaf (leaf name + keywords + parent category).

    This is what catches paraphrased documents the rule-based classifier
    would miss — a document that never says the word "termination" but
    talks about "ending the working relationship with 90 days' notice"
    still lands near the Provider Agreement prototype in embedding space
    (to the extent the active embedding provider captures that; the
    default local_hash provider captures lexical overlap, not deep
    paraphrase — see docs/decisions.md).
    """

    method_name = "embedding"

    def __init__(self, embedding_service: EmbeddingService, ontology: OntologyService):
        self.embedding_service = embedding_service
        self.ontology = ontology
        self._prototypes: dict[str, list[float]] | None = None

    def _prototype_vectors(self) -> dict[str, list[float]]:
        if self._prototypes is None:
            leaves = self.ontology.all_types()
            texts = [f"{leaf.name}. {' '.join(leaf.keywords)}. {leaf.path[-2]}." for leaf in leaves]
            vectors = self.embedding_service.embed_batch(texts)
            self._prototypes = {leaf.id: vec for leaf, vec in zip(leaves, vectors)}
        return self._prototypes

    def classify(self, doc: ClassifierInput) -> ClassifierVote:
        prototypes = self._prototype_vectors()
        doc_text = f"{doc.filename}. {' '.join(doc.headings)}. {doc.full_text[:2000]}"
        doc_vector = self.embedding_service.embed_text(doc_text)

        scores = {leaf_id: max(0.0, cosine_similarity(doc_vector, proto)) for leaf_id, proto in prototypes.items()}
        if not scores:
            return ClassifierVote(ontology_id=None, confidence=0.0, signals=[], method=self.method_name, scores={})

        best_id = max(scores, key=lambda k: (scores[k], k))
        best_score = scores[best_id]
        leaf = self.ontology.get(best_id)
        signal = f"embedding similarity to '{leaf.name}' prototype: {best_score:.2f}" if leaf else "no strong embedding match"

        return ClassifierVote(
            ontology_id=best_id,
            confidence=best_score,
            signals=[signal],
            method=self.method_name,
            scores=scores,
        )
