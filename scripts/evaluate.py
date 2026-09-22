"""POC evaluation harness (spec section 41).

Explicitly NOT a production-quality benchmark: 18 documents and 2 demo
queries is nowhere near enough to draw statistically meaningful
conclusions. This measures whether the pipeline behaves as designed
against its own golden set, for the manager demo and as a regression
check while iterating on the classifier/retrieval tuning.

Run after scripts/run_demo_ingestion.py: python scripts/evaluate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db import SessionLocal  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.retrieval.rag_factory import get_rag_service  # noqa: E402

GOLDEN_PATH = REPO_ROOT / "data" / "samples" / "golden_labels.json"
REPORT_PATH = REPO_ROOT / "data" / "processed" / "evaluation_report.json"

DEMO_QUERIES = [
    {"query": "What are the provider termination requirements?", "requester_group": "legal", "expected_document": "provider_agreement_northvalley.pdf"},
    {"query": "What reimbursement policies apply to providers?", "requester_group": "finance", "expected_document": "reimbursement_policy_outpatient.pdf"},
]


def evaluate_classification(db) -> dict:
    golden = json.loads(GOLDEN_PATH.read_text())
    docs_by_filename = {d.filename: d for d in db.query(Document).all()}

    total = len(golden)
    ontology_correct = domain_correct = review_count = 0
    misses = []

    for entry in golden:
        doc = docs_by_filename.get(entry["filename"])
        if not doc:
            misses.append({"filename": entry["filename"], "reason": "not found in database — run scripts/run_demo_ingestion.py first"})
            continue
        if doc.status == "REVIEW_REQUIRED":
            review_count += 1
        if doc.ontology_id == entry["ontology_id"]:
            ontology_correct += 1
        else:
            misses.append({
                "filename": entry["filename"], "expected": entry["ontology_id"], "predicted": doc.ontology_id,
                "confidence": doc.classification_confidence, "note": "flagged for human review, not a silent misclassification" if doc.status == "REVIEW_REQUIRED" else "misclassified",
            })
        if doc.domain == entry["domain"]:
            domain_correct += 1

    return {
        "total_documents": total,
        "ontology_accuracy": round(ontology_correct / total, 4) if total else 0.0,
        "domain_accuracy": round(domain_correct / total, 4) if total else 0.0,
        "review_rate": round(review_count / total, 4) if total else 0.0,
        "misses": misses,
    }


def evaluate_rag(db) -> dict:
    rag = get_rag_service()
    results = []
    hits = 0
    for case in DEMO_QUERIES:
        answer = rag.answer(db, case["query"], requester_group=case["requester_group"])
        top_doc = answer.citations[0].document_filename if answer.citations else None
        is_hit = top_doc == case["expected_document"]
        hits += is_hit
        results.append({
            "query": case["query"], "expected_document": case["expected_document"], "top_cited_document": top_doc,
            "precision_at_1": int(is_hit), "citation_count": len(answer.citations), "groundedness": answer.groundedness,
        })
    return {
        "queries_evaluated": len(DEMO_QUERIES),
        "precision_at_1": round(hits / len(DEMO_QUERIES), 4) if DEMO_QUERIES else 0.0,
        "citation_coverage": round(sum(1 for r in results if r["citation_count"] > 0) / len(results), 4) if results else 0.0,
        "results": results,
    }


def main() -> None:
    db = SessionLocal()
    classification = evaluate_classification(db)
    rag = evaluate_rag(db)
    db.close()

    report = {
        "disclaimer": "POC evaluation metrics against an 18-document synthetic golden set — NOT a production-quality benchmark. See docs/evaluation.md.",
        "classification": classification,
        "retrieval_and_rag": rag,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== ECIP POC Evaluation ===")
    print(f"Classification: {classification['ontology_accuracy']:.1%} ontology accuracy, "
          f"{classification['domain_accuracy']:.1%} domain accuracy, {classification['review_rate']:.1%} review rate "
          f"over {classification['total_documents']} golden documents")
    for miss in classification["misses"]:
        print(f"  - {miss['filename']}: {miss.get('note', miss.get('reason'))}")
    print(f"\nRAG: Precision@1 = {rag['precision_at_1']:.1%}, citation coverage = {rag['citation_coverage']:.1%}")
    for r in rag["results"]:
        print(f"  - {r['query']!r} -> {r['top_cited_document']} (groundedness={r['groundedness']})")
    print(f"\nFull report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
