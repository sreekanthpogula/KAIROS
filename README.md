# ECIP — Enterprise Content Intelligence Platform

**A manager-facing architecture proof-of-concept: if we had 1TB of heterogeneous enterprise files, here's how we'd understand them before we ever embed a single one.**

> We don't just embed documents, we understand them first.

ECIP is a fully-built, manually verified, end-to-end backend that ingests a heterogeneous document corpus (PDF, Word, Excel, PowerPoint, HTML, plain text, Markdown, CSV, email) and, before anything gets near a vector index, figures out **what each document actually is**: its type, its place in a controlled enterprise ontology, who is allowed to see it, how it's structured internally, and how confident the system is in all of that. Only then does it chunk, embed, and index — and every answer it later gives back carries citations and a full lineage trail to the exact page/section/chunk that produced it.

This is an architecture demonstration for engineering leadership, not a chatbot demo. The interesting part isn't "it can answer a question about a PDF" — it's the reasoning that happens *before* retrieval, and the explicit, honest trade-offs made at every stage (see [docs/decisions.md](docs/decisions.md)).

## The problem: why naive RAG breaks at enterprise scale

The default RAG recipe — `file → parse → fixed-size chunk → embed → vector DB → top-k → stuff into prompt` — works fine for a demo with twenty PDFs that all look alike. It breaks down once the corpus is large and heterogeneous, which is the normal condition of a real enterprise:

- **No file-type awareness.** A fixed-size character chunker treats a spreadsheet of claim rows exactly like contract prose. It splits tables mid-record and separates data rows from the header that gave them meaning.
- **No classification.** Every chunk is anonymous. There's no way to answer "only search financial documents" or "exclude anything this user's role shouldn't see" without re-deriving document identity from scratch, per query, from raw text.
- **No controlled ontology.** Without a shared vocabulary for "what this document is," every downstream feature (search filters, security policy, reporting) reinvents its own ad hoc categorization, and they drift out of sync with each other.
- **No security model.** Everything lands in one collection. Access control becomes a bolt-on filter over search results instead of a property the document carries from the moment it's classified.
- **No lineage.** When a RAG answer is wrong, there's no way to trace it back to a specific page, section, chunk, extractor version, or classifier version — so there's no way to debug it, either.
- **No confidence signal.** Every chunk is trusted equally. A genuinely ambiguous document (weak signals, mixed topics) gets silently filed next to a clear one with no indication anyone should double check it.

At "1TB of files" scale these failures don't average out — they compound. ECIP's answer is to spend a bounded amount of work *understanding* a document before embedding it, so that chunking, indexing, retrieval, and security all become simpler and more correct downstream, instead of harder.

## Architecture overview

Every document moves through the same 15-stage pipeline, tracked as an explicit state machine (`app/pipeline/orchestrator.py`) with one exception path: a document whose classification confidence is too low halts for a human decision instead of continuing silently.

```mermaid
flowchart LR
    A[Ingestion<br/>RECEIVED] --> B[Detect<br/>file type, no ML]
    B --> C[Validate<br/>integrity check]
    C --> D[Extract<br/>format-specific parser]
    D --> E[Classify<br/>rule + embedding + LLM blend]
    E --> F[Ontology Map<br/>domain / security defaults]
    F --> G[Enrich<br/>entities + topics]
    G -->|confidence >= 0.70| H[Segment<br/>sections / slides / sheets]
    G -->|confidence < 0.70| REV[["REVIEW_REQUIRED<br/>human-in-the-loop"]]
    REV -->|reviewer approves or corrects| H
    H --> I[Chunk<br/>type-aware selector]
    I --> J[Embed]
    J --> K[Index<br/>READY]
    K --> L[Retrieve<br/>vector + lexical + ACL]
    L --> M[Rerank<br/>explainable weighted sum]
    M --> N[Answer<br/>extractive / grounded RAG]
    N --> O[Lineage<br/>citation -> chunk -> segment -> document -> source]
```

Every stage transition is persisted as a `ProcessingEvent` (append-only, timestamped, durationed) and published on an in-process `EventBus` — the same event names and payload shapes a production deployment would push through Kafka/Event Hub (see [docs/ingestion.md](docs/ingestion.md)). Every derived record (`ClassificationResult`, `Chunk`, `Embedding`, …) carries the version of the component that produced it (`extractor_version`, `classifier_version`, `chunker_version`, `ontology_version`), so a later upgrade to any stage never silently rewrites the history of what a past decision actually was.

## Key design decisions (summary)

Full reasoning, alternatives considered, and trade-offs for each of these live in [docs/decisions.md](docs/decisions.md) as ADRs — this is just the summary:

| Decision | POC choice | Why |
|---|---|---|
| Ontology structure | Controlled taxonomy in YAML, not a knowledge graph | A closed, versioned vocabulary that non-engineers can review and edit without touching code — see [docs/ontology.md](docs/ontology.md) |
| Classification | Hybrid rules + embeddings + cost-gated LLM | No single method is universally correct at every confidence level or cost budget — see [docs/classification.md](docs/classification.md) |
| Chunking | Format-first, semantics-second selector | File structure (a slide, a worksheet) is a stronger signal than semantics when it exists — see [docs/chunking.md](docs/chunking.md) |
| Retrieval | Hybrid vector + lexical + ontology + metadata, weighted rerank | Vector-only retrieval misses exact-term matches; lexical-only misses paraphrase — see [docs/retrieval.md](docs/retrieval.md) |
| Low confidence | Route to human review, don't guess | An audit-trailed correction beats a silent, confident wrong answer — see [docs/decisions.md](docs/decisions.md) ADR-005 |
| Event architecture | In-process bus now, Kafka-shaped later | Same event contracts, no rewrite needed to swap the transport — see [docs/decisions.md](docs/decisions.md) ADR-006 |

## Ontology

Documents are classified into a single controlled ontology (`ontology/healthcare_ontology.yaml`, loaded by `app/ontology/service.py`) with **5 domains** — Clinical, Administrative, Financial, Legal, Technical — each broken into categories and leaf document types. Every leaf carries its own `document_type` label, matching `keywords`, a `chunker` hint, and the domain's `default_security_level` / `default_allowed_groups`. Classifiers may only ever resolve to a real leaf id in this file; nothing in application code hard-codes a category name. Full tree and rationale in [docs/ontology.md](docs/ontology.md).

## Classification

Every document gets a cheap, deterministic rule-based vote (filename/heading/body keyword scoring) and a local embedding-similarity vote against synthesized ontology-leaf prototypes, blended with tiered weighting that leans harder on the rule vote when it's already decisive. Only documents whose *blended* confidence lands in an uncertain middle band (0.55–0.85) — and only when an LLM is actually configured — pay for an LLM adjudication call, which is itself structurally limited to the small candidate set already narrowed down (never free text, never an invented category). Most documents never reach that stage. Full blend math, calibration constants, and the rules-vs-ML-vs-LLM trade-off discussion in [docs/classification.md](docs/classification.md).

## Type-aware chunking

Chunker selection is a two-factor decision, in priority order: **file structure first** (a `.pptx` is always chunked by slide, a `.xlsx`/`.csv` always by row-batch-with-repeated-header, an email always keeps its header attached to its body — semantics cannot override this), then **ontology-configured semantic hint second**, only for flowing-text formats (PDF/DOCX/HTML/TXT/MD) that carry no structural hint of their own — so a contract-shaped PDF and a runbook-shaped PDF, despite being "the same file format," get genuinely different chunking. Six chunkers implement this: Contract, Technical (keeps code blocks standalone), Spreadsheet, Presentation, Email, and a Generic fallback. Full decision tree and worked examples from the real sample corpus in [docs/chunking.md](docs/chunking.md).

## Hybrid retrieval

A query is understood using the same rule-based classifier that classifies documents, then candidates are narrowed by explicit filters and ACL before semantic (cosine similarity) and lexical (BM25) scoring run in parallel, and an explainable weighted-sum reranker (`0.45` semantic / `0.25` lexical / `0.20` ontology / `0.10` metadata, all configurable) produces the final ranking. RAG answers are extractive and fully deterministic in `DEMO_MODE` — no generative model, every word traceable to a retrieved chunk — with an absolute relevance floor so an access-restricted query answers "no accessible documents are relevant" honestly instead of confidently synthesizing an answer from irrelevant leftovers. This floor exists *because* of a real bug found and fixed during the build: see [docs/retrieval.md](docs/retrieval.md) for the ACL-narrowing-inflates-false-confidence story.

## Security

Every document and chunk carries a `security_level` (public/internal/confidential/restricted) and `allowed_groups`, both **derived from the ontology domain's configuration** at classification time — not scattered through application code. A human correction during review re-derives both from the corrected category. Full model and the "engineering user asks a legal question" ACL demo in [docs/security.md](docs/security.md).

## Human-in-the-loop

Any document whose blended classification confidence falls below `0.70` halts the pipeline at `REVIEW_REQUIRED` instead of continuing on a guess. A reviewer can approve the model's prediction or correct it to any other controlled ontology leaf; either action is recorded with a full audit trail (`original_prediction` vs. `human_correction` vs. `reviewer` vs. timestamp) and the pipeline automatically resumes from segmentation onward using the resolved classification. This was manually tested end-to-end: `ambiguous_mixed_memo.pdf` was corrected from Financial/Invoice to Financial/Reimbursement, the audit trail was preserved, and the document reached `READY`.

## Scale strategy

ECIP does **not** pretend to process 1TB of files in a local POC. `app/services/scale_simulator.py` instead simulates document counts, storage, throughput, and cost-aware-routing distribution at any scale (15 docs up to a "1TB" preset), calibrated two ways: ratios that describe *this POC's own measured behavior* (chunks-per-document, confidence-band distribution) are queried live from its own database; everything about a corpus this POC never loads (average enterprise document size, worker throughput) is grounded in cited public reference points (AIIM/ECM survey figures, the public MIMIC-III/IV critical-care database's documented structured-vs-free-text storage split) rather than benchmarked. Every number the simulator returns is explicitly labeled `"simulated": true`. Full detail in [docs/production-scaling.md](docs/production-scaling.md).

## Evaluation summary

Measured against the 18-document synthetic golden set (`data/samples/golden_labels.json`), evaluated by `scripts/evaluate.py` into `data/processed/evaluation_report.json`:

- **Classification: 94.4% ontology accuracy (17/18), 100% domain accuracy, 22.2% review rate.** The one ontology "miss" is `ambiguous_mixed_memo.pdf` — a document *deliberately* authored with weak, mixed signals. It scores ~0.17 confidence and correctly lands in `REVIEW_REQUIRED` rather than being silently misclassified; this is the intended human-in-the-loop demo, not a defect.
- **Confidence bands across the 18 docs:** 9 `AUTO_ACCEPT` (≥0.90), 5 `SECONDARY_VALIDATION` (0.70–0.89), 4 `REVIEW_REQUIRED` (<0.70) — the intentional ambiguous memo plus 3 spreadsheet/CSV-format financial documents that genuinely score lower because structured, tabular content carries less narrative prose for keyword+embedding text matching. This is a real, honest POC limitation, not a bug — see [docs/evaluation.md](docs/evaluation.md) for the named production fix.
- **RAG, two canonical demo queries:** Precision@1 = 100%, citation coverage = 100%, groundedness "high" (provider termination question) and "medium" (reimbursement policy question).

This is a POC evaluation on a small, synthetic golden set — a regression check and demo validator, explicitly **not** a production-quality benchmark. See [docs/evaluation.md](docs/evaluation.md) for the full honest framing.

## Running locally

ECIP runs entirely locally with **zero external services** by default: SQLite for storage, a dependency-free deterministic local-hash embedding provider, and a mock LLM provider that's simply never called unless you configure a real one (`DEMO_MODE=true` is the default in `backend/app/core/config.py`).

```bash
# from the repo root
python -m venv backend/.venv
# Windows: backend\.venv\Scripts\activate   |   macOS/Linux: source backend/.venv/bin/activate
pip install -r backend/requirements.txt

python scripts/seed_demo_data.py        # generates the 18-document synthetic corpus into data/samples/
python scripts/run_demo_ingestion.py    # runs every sample through the full pipeline
python scripts/evaluate.py              # writes data/processed/evaluation_report.json

cd backend
uvicorn app.main:app --reload           # serves the API on http://127.0.0.1:8000
```

The same flow also collapses to one command via the Makefile (`make demo`), or `powershell -File scripts/demo.ps1` on Windows without `make`:

```bash
make install   # backend venv + pip install + frontend npm install
make demo      # seed + ingest + evaluate
make backend   # uvicorn with reload
make frontend  # vite dev server
make test      # backend/tests
```

Or via Docker (`docker compose up --build`) — provisions Postgres+pgvector, backend, and frontend together; see `docker-compose.yml`.

To exercise higher-quality embeddings or a real LLM instead of the deterministic defaults, install `backend/requirements-optional.txt` and set `EMBEDDING_PROVIDER=sentence_transformers` and/or `LLM_MODE=true` + `LLM_API_KEY=...` — every provider swap is a config change, never a code change (see `backend/app/core/config.py`).

## Deploying to Vercel

The backend and frontend deploy as **two separate Vercel projects** from the same repo. Vercel's serverless functions have a read-only, ephemeral filesystem — no local disk persists between invocations — so this deployment path swaps SQLite for a real Postgres and stores uploaded file bytes in the database row itself rather than on disk (see `Document.raw_content` and `docs/decisions.md`).

**Backend project** — Root Directory: `backend`
1. In Project Settings → Root Directory, enable **"Include source files outside of the Root Directory in the Build Step"** — the backend needs the sibling `ontology/` and `data/samples/` directories at the repo root.
2. Add a Postgres database: Storage tab → Marketplace → **Neon** (Vercel's own Postgres offering was retired in favor of this integration) → Connect to this project. It auto-sets `DATABASE_URL`.
3. Set `CORS_ORIGINS` to the frontend project's URL once you have it (comma-separated if there's more than one, e.g. a preview + production URL).
4. Set `DEMO_MODE=true` (and any other overrides you want — see `.env.example`).
5. Deploy. Vercel auto-detects the FastAPI `app` instance at `backend/app/main.py`; `backend/vercel.json` sets a 60s function timeout for document processing.
6. Once deployed, run the seed + ingestion scripts against the same `DATABASE_URL` from your own machine (`DATABASE_URL=<paste> python scripts/run_demo_ingestion.py`) — there's no build-time hook that populates demo data automatically.

**Frontend project** — Root Directory: `frontend`
1. Set `VITE_API_BASE_URL` to the backend project's URL + `/api` (e.g. `https://ecip-backend.vercel.app/api`). This is a **build-time** var — set it before deploying, and redeploy (not just restart) after changing it.
2. Deploy. `frontend/vercel.json` adds the SPA fallback rewrite React Router's client-side routes need (without it, refreshing on `/documents/:id` 404s).

Then go back to the backend project and set `CORS_ORIGINS` to the frontend's actual URL (step 3 above) if you hadn't yet, and redeploy the backend.

## Demo walkthrough (5 minutes)

1. **The problem.** Naive `parse → chunk → embed` RAG has no concept of document type, ontology, security, or confidence (see above). ECIP is the alternative.
2. **Upload heterogeneous documents.** `POST /api/documents/upload` with any of the 9 formats in `data/samples/` (PDF, DOCX, XLSX, PPTX, HTML, TXT, MD, CSV, EML) — same endpoint, same response shape, format-appropriate extraction under the hood.
3. **Semantic classification.** `GET /api/documents/{id}` shows the hybrid classifier's decision, its confidence, and its `reasoning_signals` — e.g. `provider_agreement_northvalley.pdf` lands `legal.contracts.provider_agreement` at high confidence off filename + heading + body corroboration.
4. **Ontology mapping.** `GET /api/ontology` renders the full 5-domain tree with live document/chunk counts rolled up per node.
5. **Type-aware chunking.** `GET /api/documents/{id}/chunks` on `insurance_claim_report_q3.xlsx` shows row-batched chunks with the header repeated in each batch, vs. the same call on the provider agreement showing clause-sized chunks with their section heading inline.
6. **Hybrid retrieval.** `POST /api/search` with a query shows the full semantic/lexical/ontology/metadata score breakdown per result, not just a final rank.
7. **RAG question.** `POST /api/rag/query` with `"What are the provider termination requirements?"` returns a grounded, cited answer from `provider_agreement_northvalley.pdf` — Precision@1 = 100% on this canonical query.
8. **Lineage and citations.** `GET /api/documents/{id}/lineage` walks source → document → segment → chunk for any citation the RAG answer returned.
9. **Low-confidence human review.** `GET /api/reviews` shows `ambiguous_mixed_memo.pdf` pending at ~0.17 confidence; `POST /api/reviews/{id}/correct` to `financial.reimbursement.reimbursement_policy` resolves it with a full audit trail and resumes the pipeline to `READY`.
10. **Scale-to-1TB story.** `GET /api/scale-simulator?document_count=1TB` projects storage, chunk volume, and cost-aware-routing distribution at enterprise scale — explicitly labeled simulated, calibrated against this POC's own measured ratios plus cited public references, never against a real loaded dataset.

## Production evolution summary

Every POC default here has a named, deliberate production successor: SQLite → PostgreSQL+pgvector (the `VectorIndexBackend` interface already exists for this swap), the in-process `EventBus` → Kafka/Event Hub with independently-scaling consumer workers per stage, the numpy cosine vector search → native ANN indexing, the local-hash embedding → a real sentence embedding model, the weighted-sum reranker → a cross-encoder behind the same `Reranker.score()` interface, and hand-picked confidence constants → constants recalibrated against a much larger labeled sample. None of these require touching the business logic that sits above the swapped interface. Full evolution path, scaling mechanics (batching, backpressure, retries, dead-letter queues, partitioning, caching, incremental ingestion, document versioning), and a category-by-category Production Readiness Scorecard in [docs/production-scaling.md](docs/production-scaling.md).

## Documentation index

- [docs/architecture.md](docs/architecture.md) — full system architecture, layer by layer
- [docs/ontology.md](docs/ontology.md) — the controlled ontology, in depth
- [docs/ingestion.md](docs/ingestion.md) — the pipeline state machine, idempotency, event design
- [docs/classification.md](docs/classification.md) — rules vs. ML vs. LLM, the hybrid blend math
- [docs/chunking.md](docs/chunking.md) — the chunker decision tree, one section per chunker
- [docs/retrieval.md](docs/retrieval.md) — the hybrid retrieval pipeline and its explainable scoring
- [docs/security.md](docs/security.md) — the ACL model and its ontology-derived defaults
- [docs/evaluation.md](docs/evaluation.md) — the verified POC evaluation numbers, honestly framed
- [docs/decisions.md](docs/decisions.md) — ADRs for every major architectural choice
- [docs/production-scaling.md](docs/production-scaling.md) — the local-POC-to-production evolution path

## Project ground rules

Every document in the sample corpus is entirely synthetic enterprise content authored for this POC — no real patient data, no real PHI, no data sourced from any external system. Numbers describing evaluation results are measured against that synthetic 18-document golden set; numbers describing "1TB" or enterprise-scale behavior are explicitly simulated and labeled as such. Neither should be read as a production benchmark.
