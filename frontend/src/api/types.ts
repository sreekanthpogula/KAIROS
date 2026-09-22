export type IngestionStatus =
  | 'RECEIVED' | 'VALIDATED' | 'EXTRACTING' | 'EXTRACTED' | 'CLASSIFYING' | 'CLASSIFIED'
  | 'ONTOLOGY_MAPPED' | 'ENRICHED' | 'SEGMENTED' | 'CHUNKED' | 'EMBEDDING' | 'INDEXED'
  | 'READY' | 'FAILED' | 'REVIEW_REQUIRED' | 'DUPLICATE'

export type ConfidenceAction = 'AUTO_ACCEPT' | 'SECONDARY_VALIDATION' | 'REVIEW_REQUIRED'

export interface DocumentSummary {
  id: string
  filename: string
  extension: string
  mime_type: string
  size_bytes: number
  status: IngestionStatus
  domain: string | null
  document_type: string | null
  document_subtype: string | null
  ontology_id: string | null
  classification_confidence: number | null
  confidence_action: ConfidenceAction | null
  security_level: string
  created_at: string
  updated_at: string
  error_message: string | null
}

export interface DocumentDetail extends DocumentSummary {
  original_filename: string
  checksum: string
  source_system: string
  source_uri: string | null
  parser_type: string | null
  ontology_path: string[] | null
  allowed_groups: string[]
  page_count: number | null
  extractor_version: string | null
  classifier_version: string | null
  ontology_version: string | null
  chunker_version: string | null
  embedding_model: string | null
  ingestion_job_id: string | null
}

export interface ClassificationHistoryEntry {
  id: string
  document_type: string
  document_subtype: string | null
  domain: string
  ontology_id: string | null
  confidence: number
  confidence_action: string
  method: string
  reasoning_signals: string[]
  is_current: boolean
  created_at: string
}

export interface ProcessingEventOut {
  id: string
  event_type: string
  stage: string
  status: string
  message: string | null
  duration_ms: number | null
  created_at: string
}

export interface DocumentFullDetail {
  document: DocumentDetail
  classification_history: ClassificationHistoryEntry[]
  entities: { type: string; value: string; normalized_value: string; confidence: number }[]
  topics: string[]
  segments: { id: string; title: string | null; segment_type: string; level: number; parent_segment_id: string | null; page_start: number | null; page_end: number | null }[]
  chunk_count: number
  processing_events: ProcessingEventOut[]
}

export interface DocumentListResponse {
  items: DocumentSummary[]
  total: number
}

export interface ChunkOut {
  chunk_id: string
  document_id: string
  text: string
  document_type: string | null
  document_subtype: string | null
  domain: string | null
  ontology_path: string | null
  topics: string[]
  entities: string[]
  page_start: number | null
  page_end: number | null
  section: string | null
  classification_confidence: number | null
  security_level: string
  source_system: string | null
  source_uri: string | null
  parser_version: string | null
  classifier_version: string | null
  ontology_version: string | null
  chunk_index: number
  chunker_type: string
}

export interface LineageNode {
  id: string
  type: 'source' | 'document' | 'segment' | 'chunk'
  label: string
  metadata: Record<string, unknown>
}
export interface LineageEdge { source: string; target: string }
export interface LineageResponse { document_id: string; nodes: LineageNode[]; edges: LineageEdge[] }

export interface OntologyTreeNode {
  id: string
  name: string
  level: string
  path: string[]
  document_count: number
  chunk_count: number
  children: OntologyTreeNode[]
}

export interface OntologyNodeStats {
  id: string
  name: string
  level: string
  path: string[]
  document_count: number
  chunk_count: number
  top_entities: { value: string; count: number }[]
  top_topics: { topic: string; count: number }[]
  recent_documents: { id: string; filename: string; confidence: number | null; status: string }[]
}

export interface QueryUnderstandingOut {
  domain: string | null
  document_type: string | null
  ontology_id: string | null
  topics: string[]
  entities: string[]
}

export interface ScoredChunkOut {
  chunk_id: string
  document_id: string
  document_filename: string
  text: string
  section: string | null
  page_start: number | null
  page_end: number | null
  document_type: string | null
  domain: string | null
  ontology_path: string | null
  security_level: string
  semantic_score: number
  lexical_score: number
  ontology_score: number
  metadata_score: number
  final_score: number
}

export interface SearchResponse {
  query: string
  understanding: QueryUnderstandingOut
  results: ScoredChunkOut[]
  total_candidates: number
  excluded_by_acl: number
  latency_ms: number
}

export interface CitationOut {
  document_id: string
  document_filename: string
  section: string | null
  page_start: number | null
  page_end: number | null
  chunk_id: string
  final_score: number
}

export interface RAGQueryResponse {
  query: string
  answer: string
  citations: CitationOut[]
  groundedness: 'none' | 'low' | 'medium' | 'high'
  mode: string
  understanding: QueryUnderstandingOut
  scored_results: ScoredChunkOut[]
  excluded_by_acl: number
  latency_ms: number
}

export interface ReviewTaskOut {
  id: string
  document_id: string
  document_filename: string
  status: 'PENDING' | 'APPROVED' | 'CORRECTED' | 'REJECTED'
  reason: string
  original_prediction: Record<string, unknown>
  human_correction: Record<string, unknown> | null
  reviewer: string | null
  created_at: string
  resolved_at: string | null
}

export interface DashboardMetrics {
  documents_ingested: number
  processing_success_rate: number
  documents_requiring_review: number
  average_classification_confidence: number
  documents_by_status: Record<string, number>
  documents_by_type: Record<string, number>
  documents_by_domain: Record<string, number>
  documents_by_file_type: Record<string, number>
  confidence_distribution: Record<string, number>
  chunks_created: number
  embeddings_generated: number
  indexed_documents: number
  duplicate_documents: number
  failed_documents: number
  cost_aware_routing: { rule_or_embedding: number; llm_adjudicated: number; human_corrected: number }
}

export interface IngestionJobOut {
  id: string
  job_type: string
  status: string
  total_documents: number
  completed_documents: number
  review_documents: number
  failed_documents: number
  duplicate_documents: number
  avg_processing_seconds: number | null
  started_at: string
  completed_at: string | null
}

export interface IngestionJobDetail extends IngestionJobOut {
  documents: { id: string; filename: string; status: string; confidence: number | null; error_message: string | null }[]
  recent_events: { document_id: string; event_type: string; stage: string; status: string; message: string | null; duration_ms: number | null; created_at: string }[]
}

export interface ScaleSimulationResult {
  simulated: true
  inputs: { document_count: number; worker_count: number }
  storage: { estimated_total_size_gb: number; estimated_total_size_tb: number; avg_document_size_mb: number }
  volume: {
    estimated_pages: number
    estimated_chunks: number
    estimated_embeddings: number
    chunks_per_document_ratio: number
    chunks_per_document_ratio_source: string
  }
  processing: { estimated_processing_hours: number; docs_per_worker_per_hour: number }
  cost_aware_routing: { auto_deterministic_pct: number; llm_adjudicated_pct: number; human_review_pct: number; source: string }
  architecture_stages: string[]
  reference_notes: Record<string, string>
}

export interface HealthResponse {
  status: string
  app_name: string
  demo_mode: boolean
  llm_mode: boolean
  embedding_provider: string
  vector_backend: string
  database: string
}
