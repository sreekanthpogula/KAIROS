"""Deterministic, explainable classifier (spec section 12).

Scores every controlled ontology leaf by keyword overlap against the
filename, extracted headings, and body text, with filename/heading matches
weighted higher than body matches (a document titled "Provider Agreement"
is much more likely to *be* one than a document that merely mentions the
phrase once in passing). This is intentionally the highest-weighted vote in
HybridClassifier — see docs/classification.md for the rules vs. ML vs. LLM
trade-off.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from app.classifiers.base import BaseDocumentClassifier, ClassifierInput, ClassifierVote
from app.ontology.service import OntologyService

SATURATION_K = 3.5  # confidence = 1 - e^(-raw_score / K); calibrated against
# the POC golden set (data/samples/golden_labels.json) so a strong
# filename+heading+body match (~10+ raw points) saturates above 0.95 before
# the embedding vote blends in via HybridClassifier. A production system
# would recalibrate this against a much larger labeled sample (e.g. Platt
# scaling) rather than a hand-picked constant — see docs/classification.md.

_FORMAT_NATIVE_CHUNKER = {
    "xlsx": "spreadsheet",
    "csv": "spreadsheet",
    "pptx": "presentation",
    "email": "email",
}


def _keyword_variants(keyword: str) -> tuple[str, ...]:
    """Naive singular/plural tolerance for substring keyword matching
    (e.g. ontology keyword "reimbursement policy" should still match a
    query/document that says "reimbursement policies"). Not a real
    stemmer — just enough coverage for the controlled ontology's own
    keyword lists. See docs/classification.md."""
    if keyword.endswith("y") and not keyword.endswith(("ay", "ey", "iy", "oy", "uy")):
        return (keyword, keyword[:-1] + "ies")
    if keyword.endswith("s"):
        return (keyword, keyword[:-1])
    return (keyword, keyword + "s")


def _contains_any(haystack: str, keyword: str) -> bool:
    return any(v in haystack for v in _keyword_variants(keyword))


def _count_any(haystack: str, keyword: str) -> int:
    # Longest-first alternation so overlapping variants (e.g. "status" vs.
    # its naive-stripped "statu") can't double-count the same occurrence —
    # regex alternation takes the first alternative that matches at each
    # position, and findall never re-matches consumed characters.
    variants = sorted(set(_keyword_variants(keyword)), key=len, reverse=True)
    pattern = "|".join(re.escape(v) for v in variants)
    return len(re.findall(pattern, haystack))


class RuleBasedClassifier(BaseDocumentClassifier):
    method_name = "rule"

    def __init__(self, ontology: OntologyService):
        self.ontology = ontology

    def classify(self, doc: ClassifierInput) -> ClassifierVote:
        filename_tokens = re.sub(r"[_\-.]", " ", Path(doc.filename).stem).lower()
        heading_text = " ".join(doc.headings).lower()
        body_text = doc.full_text.lower()

        scores: dict[str, float] = {}
        signal_map: dict[str, list[tuple[float, str]]] = {}

        for leaf in self.ontology.all_types():
            raw_score = 0.0
            signals: list[tuple[float, str]] = []

            for kw in leaf.keywords:
                if _contains_any(filename_tokens, kw):
                    raw_score += 3.0
                    signals.append((3.0, f"filename mentions '{kw}'"))
                if _contains_any(heading_text, kw):
                    raw_score += 2.5
                    signals.append((2.5, f"heading mentions '{kw}'"))
                hits = _count_any(body_text, kw)
                if hits:
                    weight = min(hits, 3) * 1.0
                    raw_score += weight
                    signals.append((weight, f"body mentions '{kw}'" + (f" ({hits}x)" if hits > 1 else "")))

            native_chunker = _FORMAT_NATIVE_CHUNKER.get(doc.parser_type)
            if native_chunker and leaf.chunker == native_chunker:
                raw_score += 1.0
                signals.append((1.0, f"{doc.parser_type} format is consistent with {leaf.chunker} content"))

            if raw_score > 0:
                scores[leaf.id] = raw_score
                signal_map[leaf.id] = signals

        if not scores:
            return ClassifierVote(ontology_id=None, confidence=0.0, signals=["no keyword signals matched any ontology category"], method=self.method_name, scores={})

        best_id = max(scores, key=lambda k: (scores[k], k))
        best_score = scores[best_id]
        confidence = 1.0 - math.exp(-best_score / SATURATION_K)

        top_signals = [s for _, s in sorted(signal_map[best_id], key=lambda p: p[0], reverse=True)[:6]]

        return ClassifierVote(
            ontology_id=best_id,
            confidence=min(confidence, 0.99),
            signals=top_signals,
            method=self.method_name,
            scores=scores,
        )
