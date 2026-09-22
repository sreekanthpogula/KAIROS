"""LLM adjudication for ambiguous cases only (spec sections 12 & 63).

HybridClassifier invokes this stage exclusively when rule+embedding
confidence lands in an uncertain middle band AND LLM_MODE is actually
configured — never for every document. The LLM is structurally
constrained to the small candidate set HybridClassifier already narrowed
down to, so it is impossible for it to "invent" a category outside the
controlled ontology (spec section 13).
"""
from __future__ import annotations

import json
import re

from app.classifiers.base import BaseDocumentClassifier, ClassifierInput, ClassifierVote
from app.ontology.service import OntologyService
from app.services.llm_provider import BaseLLMProvider

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_PROMPT = (
    "You are a document classification adjudicator for a controlled enterprise ontology. "
    "You MUST choose exactly one ontology_id from the provided list — never invent a new one. "
    'Respond with strict JSON only: {"ontology_id": "<one of the listed ids>", "confidence": <0.0-1.0>, "reason": "<short reason>"}'
)


class LLMClassifier(BaseDocumentClassifier):
    method_name = "llm"

    def __init__(self, llm_provider: BaseLLMProvider, ontology: OntologyService):
        self.llm = llm_provider
        self.ontology = ontology

    def classify(self, doc: ClassifierInput) -> ClassifierVote:
        all_ids = [leaf.id for leaf in self.ontology.all_types()]
        return self.classify_among(doc, all_ids)

    def classify_among(self, doc: ClassifierInput, candidate_ids: list[str]) -> ClassifierVote:
        candidates = [self.ontology.get(cid) for cid in candidate_ids if self.ontology.get(cid)]
        if not candidates:
            return ClassifierVote(ontology_id=None, confidence=0.0, signals=[], method=self.method_name, scores={})

        options_text = "\n".join(f"- {c.id}: {' / '.join(c.path)}" for c in candidates)
        user_prompt = (
            f"Document filename: {doc.filename}\n"
            f"Headings: {'; '.join(doc.headings[:8]) or '(none extracted)'}\n"
            f"Excerpt: {doc.full_text[:1500]}\n\n"
            f"Ontology options:\n{options_text}\n\n"
            "Which ontology_id best matches this document?"
        )

        raw = self.llm.complete(_SYSTEM_PROMPT, user_prompt, max_tokens=200)
        parsed = self._parse(raw)

        if not parsed or parsed.get("ontology_id") not in candidate_ids:
            return ClassifierVote(
                ontology_id=None,
                confidence=0.0,
                signals=["LLM adjudication unavailable or returned an out-of-ontology answer — ignored"],
                method=self.method_name,
                scores={},
            )

        confidence = float(parsed.get("confidence", 0.75))
        reason = parsed.get("reason", "").strip()
        return ClassifierVote(
            ontology_id=parsed["ontology_id"],
            confidence=max(0.0, min(confidence, 0.99)),
            signals=[f"LLM adjudication: {reason}" if reason else "LLM adjudication (no reason given)"],
            method=self.method_name,
            scores={parsed["ontology_id"]: confidence},
        )

    @staticmethod
    def _parse(raw: str) -> dict | None:
        match = _JSON_RE.search(raw)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
