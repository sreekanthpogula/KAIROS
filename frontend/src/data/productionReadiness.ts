export interface ScorecardRow {
  category: string
  poc: string
  production: string
}

export const PRODUCTION_READINESS: ScorecardRow[] = [
  { category: 'Ingestion', poc: 'Synchronous FastAPI upload + in-process pipeline orchestrator', production: 'Object storage (S3/ADLS/GCS) event notifications → Kafka/Event Hub → independently-scaling ingestion workers' },
  { category: 'Classification', poc: 'Rule + local-hash-embedding hybrid, LLM adjudication only in an uncertain confidence band', production: 'Same tiered routing, with a trained/calibrated model replacing the rule-based vote and a managed LLM endpoint with rate limiting and cost monitoring' },
  { category: 'Ontology', poc: 'Single YAML file, loaded into memory and materialized into one ontology_nodes table', production: 'Versioned ontology service with change approval workflow, backward-compatible migrations, and multi-tenant ontology support' },
  { category: 'Chunking', poc: 'Format-first/semantics-second chunker selection, six chunker implementations', production: 'Same decision tree, with per-chunker tuning validated against retrieval eval metrics and configurable per business unit' },
  { category: 'Retrieval', poc: 'Numpy cosine similarity + BM25 rebuilt per query, weighted-sum reranker', production: 'pgvector/dedicated vector DB with ANN indexing, persistent inverted index, and a cross-encoder reranker' },
  { category: 'Security', poc: 'security_level + allowed_groups derived from ontology defaults, enforced in application code', production: 'Same model backed by real identity/SSO groups, row-level security at the database layer, audit logging of every access' },
  { category: 'Observability', poc: 'ProcessingEvent rows + structured stage timing, in-process event bus', production: 'Kafka/Event Hub topics, distributed tracing, metrics pipeline (Prometheus/Datadog), alerting on stage failure rates' },
  { category: 'Scalability', poc: 'Single process, single SQLite/Postgres instance, ~dozens of documents', production: 'Horizontally-scaled worker pools per stage, partitioned storage, backpressure and dead-letter queues, batch embedding at scale' },
  { category: 'Reliability', poc: 'Idempotent retry via checksum dedup + clear-and-recreate on resume', production: 'Per-stage checkpointing, exactly-once semantics via the event bus, automated retry policies with exponential backoff' },
  { category: 'Evaluation', poc: '18-document golden set, 2 canonical demo queries, POC-only metrics', production: 'Continuously-updated golden set, statistically significant sample sizes, A/B testing of classifier/retrieval changes before rollout' },
]
