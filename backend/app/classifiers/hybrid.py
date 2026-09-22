"""Orchestrates rule + embedding + (conditionally) LLM votes into a single
controlled-ontology decision (spec section 12).

This is the cost-aware routing story from spec section 63 in code: every
document gets the cheap deterministic rule pass and the local embedding
pass; only documents whose combined confidence lands in an uncertain
middle band — AND only when LLM_MODE is actually configured — pay for an
LLM call. Most documents never reach stage 4.
"""
from __future__ import annotations

import math

from app.classifiers.base import ClassifierInput
from app.classifiers.embedding_based import EmbeddingClassifier
from app.classifiers.llm_based import LLMClassifier
from app.classifiers.rule_based import SATURATION_K, RuleBasedClassifier
from app.core.config import Settings
from app.ontology.service import OntologyService
from app.schemas.classification import ClassificationOutput
from app.services.confidence import ConfidenceService

RULE_WEIGHT = 0.7
EMBEDDING_WEIGHT = 0.3
LLM_BAND_LOW = 0.55
LLM_BAND_HIGH = 0.85
TOP_K_CANDIDATES = 3

# The local_hash embedding provider compares a short ontology-leaf prototype
# (name + keywords) against a much longer document text, which structurally
# dampens bag-of-hashed-terms cosine similarity even for an on-topic match.
# EMBEDDING_CALIBRATION corrects for that length-mismatch bias so the
# embedding vote's *scale* is comparable to the rule vote's before blending.
# A learned embedding model would not need this — see docs/decisions.md.
EMBEDDING_CALIBRATION = 1.35


def _rule_confidence(raw_score: float) -> float:
    return min(1.0 - math.exp(-raw_score / SATURATION_K), 0.99)


def _calibrated_embedding_confidence(raw_similarity: float) -> float:
    return min(raw_similarity * EMBEDDING_CALIBRATION, 0.99)


# When filename + heading + body all independently corroborate the same
# leaf (rule_conf >= DOMINANT_RULE_THRESHOLD), that agreement is stronger
# evidence than a single embedding comparison against a short prototype
# can meaningfully override — so the blend leans further toward the rule
# vote. Below that threshold (a contested or weak rule signal) the
# embedding vote gets its full normal weight to help disambiguate, which
# is exactly the case it's useful for. See docs/classification.md.
DOMINANT_RULE_THRESHOLD = 0.95
DOMINANT_RULE_WEIGHT = 0.85
DOMINANT_EMBEDDING_WEIGHT = 0.15


def _blend(rule_conf: float, emb_conf: float) -> float:
    if rule_conf >= DOMINANT_RULE_THRESHOLD:
        return DOMINANT_RULE_WEIGHT * rule_conf + DOMINANT_EMBEDDING_WEIGHT * emb_conf
    return RULE_WEIGHT * rule_conf + EMBEDDING_WEIGHT * emb_conf


def _top_k_ids(scores: dict[str, float], k: int) -> list[str]:
    return [cid for cid, _ in sorted(scores.items(), key=lambda p: p[1], reverse=True)[:k]]


class HybridClassifier:
    method_name = "hybrid"

    def __init__(
        self,
        rule_classifier: RuleBasedClassifier,
        embedding_classifier: EmbeddingClassifier,
        llm_classifier: LLMClassifier,
        ontology: OntologyService,
        confidence_service: ConfidenceService,
        settings: Settings,
    ):
        self.rule = rule_classifier
        self.embedding = embedding_classifier
        self.llm = llm_classifier
        self.ontology = ontology
        self.confidence_service = confidence_service
        self.settings = settings

    def classify(self, doc: ClassifierInput) -> ClassificationOutput:
        rule_vote = self.rule.classify(doc)
        embedding_vote = self.embedding.classify(doc)

        candidate_ids = set(_top_k_ids(rule_vote.scores, TOP_K_CANDIDATES)) | set(
            _top_k_ids(embedding_vote.scores, TOP_K_CANDIDATES)
        )

        if not candidate_ids:
            return self._unclassifiable(rule_vote.signals + embedding_vote.signals)

        combined_scores: dict[str, float] = {}
        for cid in candidate_ids:
            rule_conf = _rule_confidence(rule_vote.scores.get(cid, 0.0))
            emb_conf = _calibrated_embedding_confidence(embedding_vote.scores.get(cid, 0.0))
            combined_scores[cid] = _blend(rule_conf, emb_conf)

        best_id = max(combined_scores, key=lambda k: (combined_scores[k], k))
        combined_confidence = combined_scores[best_id]

        signals = list(dict.fromkeys(rule_vote.signals + embedding_vote.signals))  # de-dup, keep order
        method = "hybrid"
        raw_scores = {
            "rule_score": rule_vote.scores.get(best_id, 0.0),
            "rule_confidence": round(_rule_confidence(rule_vote.scores.get(best_id, 0.0)), 4),
            "embedding_score": round(embedding_vote.scores.get(best_id, 0.0), 4),
            "combined_confidence_pre_llm": round(combined_confidence, 4),
        }

        if LLM_BAND_LOW <= combined_confidence < LLM_BAND_HIGH and self.settings.effective_llm_mode:
            llm_vote = self.llm.classify_among(doc, sorted(candidate_ids))
            raw_scores["llm_invoked"] = True
            if llm_vote.ontology_id:
                best_id = llm_vote.ontology_id
                combined_confidence = llm_vote.confidence
                signals = signals + llm_vote.signals
                method = "hybrid+llm"
                raw_scores["llm_confidence"] = round(llm_vote.confidence, 4)
        else:
            raw_scores["llm_invoked"] = False

        if not self.ontology.resolve_or_none(best_id):
            return self._unclassifiable(signals)

        domain_node = self.ontology.domain_of(best_id)
        confidence_action = self.confidence_service.action_for(combined_confidence)

        return ClassificationOutput(
            document_type=self.ontology.document_type_for(best_id) or "unknown",
            document_subtype=self.ontology.document_subtype_for(best_id),
            domain=domain_node.id if domain_node else "unknown",
            confidence=round(combined_confidence, 4),
            reasoning_signals=signals[:8] or ["no strong signals — routed on nearest available match"],
            method=method,
            raw_scores=raw_scores,
            ontology_id=best_id,
            confidence_action=confidence_action,
            classifier_version=self.settings.classifier_version,
            ontology_version=self.ontology.version,
        )

    def _unclassifiable(self, signals: list[str]) -> ClassificationOutput:
        return ClassificationOutput(
            document_type="unclassified",
            document_subtype=None,
            domain="unknown",
            confidence=0.0,
            reasoning_signals=signals or ["no keyword or embedding signal matched any controlled ontology category"],
            method=self.method_name,
            raw_scores={},
            ontology_id=None,
            confidence_action=self.confidence_service.action_for(0.0),
            classifier_version=self.settings.classifier_version,
            ontology_version=self.ontology.version,
        )
