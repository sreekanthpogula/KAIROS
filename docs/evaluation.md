# Evaluation

## What this is, and what it is not

`scripts/evaluate.py`'s own module docstring says it plainly: *"Explicitly NOT a production-quality benchmark: 18 documents and 2 demo queries is nowhere near enough to draw statistically meaningful conclusions. This measures whether the pipeline behaves as designed against its own golden set, for the manager demo and as a regression check while iterating on the classifier/retrieval tuning."*

Every number on this page is measured against a small, entirely synthetic, hand-authored golden set (`data/samples/golden_labels.json`, 18 documents) and written by `scripts/evaluate.py` to `data/processed/evaluation_report.json`, which itself opens with the same disclaimer: *"POC evaluation metrics against an 18-document synthetic golden set — NOT a production-quality benchmark."* Treat this page as evidence the pipeline does what it was designed to do, not as a claim about how it would perform on a real, large, messy enterprise corpus.

## Classification results

From `data/processed/evaluation_report.json`:

| Metric | Value |
|---|---|
| Total golden documents | 18 |
| Ontology accuracy | **94.4%** (17/18) |
| Domain accuracy | **100%** |
| Review rate | **22.2%** (4/18) |

Confidence-band distribution across all 18 documents (measured, not in the JSON report directly but tracked in `TODO.md`'s calibration notes and consistent with the review rate above): **9 `AUTO_ACCEPT`** (≥0.90), **5 `SECONDARY_VALIDATION`** (0.70–0.89), **4 `REVIEW_REQUIRED`** (<0.70).

### The one ontology "miss" is an intended outcome, not an error

```json
{
  "filename": "ambiguous_mixed_memo.pdf",
  "expected": "financial.reimbursement.reimbursement_policy",
  "predicted": "financial.invoices.hospital_invoice",
  "confidence": 0.174,
  "note": "flagged for human review, not a silent misclassification"
}
```

`ambiguous_mixed_memo.pdf` is *deliberately* authored with weak, mixed invoice/reimbursement signals and no dominant heading (`scripts/seed_demo_data.py: build_ambiguous_document` — the docstring there says exactly this: *"Deliberately weak-signal document for the low-confidence / human review demo scenario... classifier is expected to land in the 0.50-0.65 confidence band"*; it landed lower still, at ~0.17, once actually calibrated). The measured outcome is the intended one: the classifier's best guess is wrong, but its confidence (0.174) is far below the 0.70 review threshold, so the document is correctly routed to `REVIEW_REQUIRED` instead of being silently filed under the wrong category. A human reviewer then corrects it — the demo's canonical review scenario is exactly this document, corrected from Financial/Invoice to Financial/Reimbursement, with the full audit trail (`original_prediction` vs. `human_correction` vs. `reviewer` vs. `timestamp`) preserved on the `ReviewTask` row. **The system being "wrong" here is the point**: an honest low-confidence wrong guess that gets caught is a working safety net; a confident wrong guess would be a silent failure.

### Three more documents land in REVIEW_REQUIRED for a different, equally honest reason

The remaining 3 of the 4 `REVIEW_REQUIRED` documents are the corpus's spreadsheet/CSV-format financial documents — the only three documents in the entire 18-document corpus that are both financial in content *and* tabular in format (`insurance_claim_report_q3.xlsx`, `financial_report_q3_2026.xlsx`, `claims_export_q3.csv`). This is a genuine, honestly-surfaced POC limitation:

- Rule-based and embedding-based classification both score primarily against **narrative prose** — sentences that contain the domain's keywords in context.
- A spreadsheet's content is mostly column headers, codes, and numbers (`Claim ID | Provider | Payer | CPT Code | Billed Amount | Paid Amount | Status | Date`, followed by rows of exactly that). It never *says* "reimbursement rate" or "claims processing" in a sentence, even though a human glancing at the column headers immediately recognizes the document's category.
- The result is genuinely lower classification confidence for structurally tabular documents — not a bug in the scoring math, but a real gap in what signals the current classifier looks at.

**Named production fix**: a schema/column-header-aware classification signal — a rule (or learned) component that scores a spreadsheet's *column headers and structural shape* directly (e.g. `CPT Code` + `Billed Amount` + `Paid Amount` strongly implies `financial.claims`, independent of any narrative sentence), rather than relying on the same prose-oriented keyword/embedding scoring used for flowing text. This is explicitly the kind of improvement that belongs in [decisions.md](decisions.md) and [production-scaling.md](production-scaling.md) rather than something to quietly patch around — it's a real, named gap, not paper over it as if classification were uniformly strong across formats.

## Retrieval and RAG results

From `data/processed/evaluation_report.json`, evaluated on the two canonical demo queries defined in `scripts/evaluate.py`:

| Query | Requester group | Expected document | Top cited document | Precision@1 | Citations | Groundedness |
|---|---|---|---|---|---|---|
| "What are the provider termination requirements?" | legal | `provider_agreement_northvalley.pdf` | `provider_agreement_northvalley.pdf` | 1.0 | 3 | high |
| "What reimbursement policies apply to providers?" | finance | `reimbursement_policy_outpatient.pdf` | `reimbursement_policy_outpatient.pdf` | 1.0 | 3 | medium |

**Precision@1 = 100%, citation coverage = 100%** across both queries — every answer cited its expected source document as the top result, and every answer carried at least one citation (in fact exactly 3 each). The groundedness difference (`high` vs. `medium`) reflects the two queries' different final-score margins ([retrieval.md](retrieval.md) explains the calibration: `>= 0.45` final score is "high," `>= 0.30` is "medium") — both are real, correctly-answered results, just with different score strength, not a pass/fail distinction.

## How to reproduce these numbers

```bash
python scripts/seed_demo_data.py      # (re)generates the 18-document corpus + golden_labels.json
python scripts/run_demo_ingestion.py  # runs every document through the full pipeline
python scripts/evaluate.py            # writes data/processed/evaluation_report.json and prints a summary
```

`evaluate_classification()` compares each golden document's actual `Document.ontology_id`/`domain`/`status` against its golden label; `evaluate_rag()` runs the two demo queries through the real `RAGService` and checks whether the top citation matches the expected document. Nothing here is hand-computed or asserted independently of the running pipeline — the report file is machine-written by actually exercising the code documented elsewhere in `docs/`.

## Why 18 documents and 2 queries is the right size for this artifact, and the wrong size for a claim

This corpus and query set exist to make a specific, falsifiable set of behaviors demonstrable and regression-checkable: does classification route confidently-correct documents to `AUTO_ACCEPT`, does it route the genuinely ambiguous one to review, does hybrid retrieval find the right document for a well-formed question, does ACL filtering correctly withhold an answer instead of hallucinating one. All of those are yes/no questions that 18 documents can answer clearly. None of the numbers above ("94.4% accuracy," "100% precision@1") should be read as an estimate of what accuracy or precision would look like on a real enterprise corpus with thousands of documents, genuine ambiguity, inconsistent authoring quality, and OCR noise — that would require a much larger, independently-labeled evaluation set, which is explicitly out of scope for this POC. See [production-scaling.md](production-scaling.md) for what a production evaluation program would need to look like instead.
