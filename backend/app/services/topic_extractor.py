"""Normalized topic extraction (spec section 17).

Deliberately a small, fixed, controlled vocabulary — the spec explicitly
warns against generating "hundreds of synonyms". Each topic id maps to a
short trigger-phrase list; a document either surfaces a topic or it
doesn't, there is no scoring nuance beyond "matched".
"""
from __future__ import annotations

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "termination": ["termination", "terminate"],
    "reimbursement": ["reimbursement", "reimburse"],
    "provider_network_participation": ["network participation", "in-network", "panel status", "credentialing"],
    "compliance": ["compliance", "hipaa", "privacy rule", "security rule", "breach notification"],
    "patient_eligibility": ["eligibility", "eligible"],
    "claims_processing": ["claim", "adjudication", "denial"],
    "billing_invoicing": ["invoice", "amount due", "bill to"],
    "financial_performance": ["revenue", "financial summary", "financial performance", "payment volume"],
    "clinical_care_standards": ["standard of care", "clinical guideline", "care guideline", "evidence-based"],
    "incident_response": ["incident response", "rollback", "on-call", "runbook", "escalation"],
    "system_architecture": ["architecture", "api design", "system design", "service boundary"],
    "regulatory_requirements": ["regulation", "cfr", "regulatory", "statute"],
    "employee_benefits": ["benefits", "health plan", "premium", "deductible", "enrollment"],
    "meeting_governance": ["meeting notes", "action items", "attendees", "agenda"],
}


def extract_topics(text: str, max_topics: int = 6) -> list[str]:
    lowered = text.lower()
    scored: list[tuple[str, int]] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        hits = sum(lowered.count(kw) for kw in keywords)
        if hits > 0:
            scored.append((topic, hits))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [topic for topic, _ in scored[:max_topics]]
