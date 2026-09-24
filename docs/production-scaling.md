# Production Scaling

This document is explicit about a single point: **this POC is not production-ready, and isn't trying to be.** It's an architecture demonstration — every interface in it is shaped so a production implementation can be swapped in behind it, but almost none of those production implementations are actually built here. This page describes the evolution path from the local POC to that production shape, and is honest about the gap at every step.

## The evolution, layer by layer

| Layer | Local POC (what's actually running) | Production target (what it's shaped for) |
|---|---|---|
| Storage | SQLite, single file, `data/kcip.db` | PostgreSQL, managed/HA, connection pooling |
| Vector index | numpy cosine similarity, in-process, recomputed per query | pgvector (ANN index — HNSW/IVFFlat) or a dedicated vector database |
| Lexical index | BM25 (`rank_bm25`), rebuilt fresh per query over the candidate set | Persistent inverted index (Postgres `tsvector`/GIN, or a dedicated search engine) |
| Object storage | Local filesystem (`data/raw/`, `data/samples/`) | S3 / Azure Data Lake Storage / GCS |
| Event transport | In-process `EventBus`, synchronous function calls | Kafka / Event Hub / PubSub, durable topics, consumer groups |
| Compute | Single FastAPI process, synchronous pipeline execution | Independently-scaling worker pools per pipeline stage |
| Embeddings | `local_hash` (dependency-free feature hashing) | `sentence_transformers` or a hosted embeddings API |
| LLM adjudication / RAG generation | Mock provider (never called unless configured) | A real OpenAI-compatible provider, rate-limited and monitored |
| Migrations | `Base.metadata.create_all()` at startup | Alembic revisions |

None of these swaps are hypothetical rewrites — every one of them sits behind an interface that already exists in this codebase (`VectorIndexBackend`, `EmbeddingProvider`, `BaseLLMProvider`, `BaseExtractor`, `EventBus`), selected today via a factory function or a `Settings` value. The work to actually make each swap is provisioning and testing the real backing service, not redesigning the code that calls it.

## Scaling mechanics that don't exist yet, and what they'd need to look like

The POC's "clear and recreate" idempotency approach ([ingestion.md](ingestion.md)) and synchronous in-process event bus ([decisions.md](decisions.md) ADR-006) are honest simplifications that work at POC volume and stop being adequate well before real enterprise volume. Here's what each production concern actually requires:

- **Horizontal scaling.** Each pipeline stage (extract, classify, chunk, embed) becomes its own consumer group reading from its own topic, scaled independently by its own bottleneck — extraction is CPU/format-bound, classification's LLM-gated tail is latency- and rate-limit-bound, embedding is batchable and often GPU-bound. Nothing in the POC's stage functions assumes single-process execution; the orchestrator's per-stage methods are already the natural unit boundary for this split.
- **Batching.** `EmbeddingService.embed_batch()` already batches within a document; production batching needs to happen *across* documents too (accumulate N chunks across however many documents arrived recently, embed once) to amortize API/GPU call overhead — the POC's per-document batching doesn't need this because it never runs at a volume where per-call overhead matters.
- **Backpressure.** The POC has none — `ingest_document()` runs the full pipeline synchronously and returns. A queue-based production system needs consumers that can signal "slow down" upstream (via consumer lag, queue depth, or explicit rate limiting) rather than accepting unbounded work.
- **Retries.** `retry_document()` exists today as an operator-triggered, manual action against a `FAILED` document. Production needs automatic retry with backoff at the message-consumption level (a transient extraction failure or a rate-limited LLM call shouldn't require a human to notice and click retry) — with a cap, so retries don't become the new backpressure problem.
- **Dead-letter queues.** Doesn't exist yet — a document that fails processing repeatedly needs to land somewhere it can be inspected and reprocessed later, rather than either blocking a queue or being silently dropped. The `FAILED` status plus `error_message` field are the seed of this (a document is never left in an ambiguous state), but there's no automated "moved to DLQ after N attempts" behavior.
- **Idempotency at higher volume.** The POC's checksum-based dedup at receive time ([ingestion.md](ingestion.md)) scales fine — it's a single indexed lookup regardless of corpus size. The "clear and recreate derived rows on retry" approach does not scale as well once a single document's derived data (chunks, embeddings) is expensive to recompute; a production system would want per-stage checkpointing so a failure after chunking doesn't force re-embedding chunks that were already embedded successfully.
- **Partitioning.** Not implemented — the POC's single SQLite file has no partitioning story at all. Production would partition by tenant and/or by domain (the ontology's 5 domains are a natural partition key for both storage sharding and independent retention/security policy application).
- **Caching.** Not implemented. Obvious candidates: query embedding cache (repeated queries shouldn't re-embed), ontology-prototype embeddings (`EmbeddingClassifier._prototype_vectors()` already caches these in-process per instance, but not across restarts or processes), and reranker inputs for identical repeated queries.
- **Incremental ingestion.** The POC only ever processes a document once end-to-end; there's no notion of "this source system's document changed, re-ingest only the delta." Production would need change-detection (a version/etag from the source system, not just a content checksum) and a defined behavior for what happens to old chunks/embeddings when a document is updated rather than newly created.
- **Document versioning.** `checksum` uniquely identifies *content*, not a logical document's lifecycle — a new version of the same logical document (say, an updated Provider Agreement) is currently indistinguishable from an unrelated new document unless something outside this system tracks that relationship. Production needs an explicit `document_family_id`/`version` concept, superseding old chunks/embeddings on new-version ingestion rather than leaving both indexed as if they were independent, unrelated documents.

## The Scale Simulator: what it actually models, and how it's calibrated

`app/services/scale_simulator.py` exists specifically because this POC's answer to "what happens at 1TB" should not be "we made something up," nor "we actually loaded 1TB of files to find out" (infeasible for a local POC, and unnecessary — the pipeline logic doesn't change based on volume, only the infrastructure running it does). Instead, it **simulates** document counts, storage, throughput, and cost-aware-routing distribution at any requested scale, calibrated two different ways depending on what's being estimated:

1. **Ratios measured from this POC's own real database** — chunks-per-document (`_measured_chunks_per_document`, a live query against this POC's actual `Document`/`Chunk` tables) and the confidence-band distribution (`_measured_confidence_bands`, a live query against `ClassificationResult`). These are real numbers from real (if small) measured behavior, not invented.
2. **Publicly-documented reference points, for everything this POC never loads** — average enterprise document size (2.4 MB, blending AIIM/ECM industry survey figures for native office documents and scanned/OCR'd pages), worker throughput (150 docs/worker/hour, an illustrative planning estimate, explicitly *not* a benchmark of this codebase under load), and the "80–90% of enterprise content is unstructured" finding commonly cited from AIIM surveys — the core justification for this POC's whole ingestion architecture. The module also cites the public MIMIC-III/IV critical-care database's documented ~6GB of structured ICU data alongside a much larger free-text clinical-notes companion release, as commonly-cited evidence that free-text clinical documentation dominates storage volume in a real healthcare enterprise — referenced for context only; this POC's corpus is entirely synthetic and never loads or benchmarks against MIMIC data.

Every number the simulator's API response (`GET /api/scale-simulator`) returns is explicitly labeled `"simulated": true`, and each reference figure's provenance is returned inline under `reference_notes` rather than presented as an unsourced constant. The "1TB" preset resolves to an implied document count (`1TB / 2.4MB ≈ 437,000 documents`) purely so the rest of the simulation only has to reason in document counts — it is an illustrative figure for planning conversation, not a claim about any real corpus's actual composition.

## Production Readiness Scorecard

| Category | POC implementation | Production next step |
|---|---|---|
| **Ingestion** | Synchronous, single-process, in-memory pipeline per document; checksum dedup at receive | Async, queue-driven, independently-scaling workers per stage; backpressure and rate limiting at the queue |
| **Classification** | Hybrid rule+embedding blend, hand-calibrated constants against an 18-doc golden set; LLM gated to a confidence band | Constants recalibrated (e.g. Platt scaling) against a large labeled sample; schema/column-header-aware signal for tabular documents; per-domain confidence thresholds |
| **Ontology** | Single YAML file, one healthcare domain tree, loaded at startup | Ontology authoring/review workflow, multi-tenant ontology support, versioned rollout with backward-compatible migration of existing classifications |
| **Chunking** | Six format/semantic chunkers, hand-tuned `MAX_CHARS` per type | Chunk-size tuning validated against retrieval quality metrics, not just "seems reasonable"; adaptive chunk sizing by embedding-model context window |
| **Retrieval** | numpy cosine vector search + per-query-rebuilt BM25 + weighted-sum rerank | pgvector/dedicated vector DB with ANN indexing; persistent lexical index; cross-encoder reranker behind the existing `Reranker.score()` interface |
| **Security** | `security_level`/`allowed_groups` derived from ontology domain defaults; group passed as a request parameter | Real IdP/SSO-derived group membership; row/field-level redaction; access-denial audit logging; encryption at rest and in transit |
| **Observability** | `ProcessingEvent` audit log, `ClassificationResult` history, `GET /api/metrics` aggregation | Structured logging, distributed tracing across worker pools, metrics export to a real monitoring stack (Prometheus/Grafana or equivalent), alerting on stage failure rates |
| **Scalability** | Single process, single SQLite file, no partitioning | Horizontal worker scaling per stage, tenant/domain partitioning, caching layer (query embeddings, ontology prototypes, rerank inputs) |
| **Reliability** | Manual retry of `FAILED` documents; no automated retry, no dead-letter queue | Automatic retry with backoff at the consumer level; dead-letter queues with inspection tooling; per-stage checkpointing instead of clear-and-recreate |
| **Evaluation** | 18-document synthetic golden set, 2 demo queries, regression-check-only | Large, independently-labeled evaluation corpus; statistically meaningful sample sizes; continuous evaluation against production traffic samples (with privacy safeguards) |

## The honest bottom line

Every POC default documented across `docs/` was chosen to prove a specific architectural point — that document understanding should happen before embedding, that confidence should gate automation, that security should be a property of classification rather than a bolt-on, that every interface should be swappable without touching its callers — while running entirely locally with zero external dependencies. None of those defaults were chosen because they're what a production deployment should actually run at scale, and this page is where that gap is spelled out explicitly rather than left implicit.
