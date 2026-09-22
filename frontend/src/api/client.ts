import type {
  DashboardMetrics,
  DocumentFullDetail,
  DocumentListResponse,
  HealthResponse,
  IngestionJobDetail,
  IngestionJobOut,
  LineageResponse,
  OntologyNodeStats,
  OntologyTreeNode,
  RAGQueryResponse,
  ReviewTaskOut,
  ScaleSimulationResult,
  SearchResponse,
} from './types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json', ...init?.headers } : init?.headers,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${body}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  uploadDocument: (file: File, sourceSystem = 'demo-sharepoint') => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_system', sourceSystem)
    return request<{ document_id: string; ingestion_status: string; is_duplicate: boolean }>('/documents/upload', { method: 'POST', body: form })
  },

  listDocuments: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== '' && qs.set(k, String(v)))
    return request<DocumentListResponse>(`/documents?${qs.toString()}`)
  },
  getDocument: (id: string) => request<DocumentFullDetail>(`/documents/${id}`),
  getDocumentLineage: (id: string) => request<LineageResponse>(`/documents/${id}/lineage`),
  getDocumentChunks: (id: string) => request<import('./types').ChunkOut[]>(`/documents/${id}/chunks`),
  retryDocument: (id: string) => request(`/documents/${id}/retry`, { method: 'POST' }),

  getOntologyTree: () => request<OntologyTreeNode & { document_count: number; chunk_count: number }>('/ontology'),
  getOntologyNode: (id: string) => request<OntologyNodeStats>(`/ontology/${id}`),

  search: (body: { query: string; requester_group?: string; domain_filter?: string; document_type_filter?: string; top_k?: number }) =>
    request<SearchResponse>('/search', { method: 'POST', body: JSON.stringify(body) }),

  ragQuery: (body: { query: string; requester_group?: string; domain_filter?: string; document_type_filter?: string }) =>
    request<RAGQueryResponse>('/rag/query', { method: 'POST', body: JSON.stringify(body) }),

  listReviews: (statusFilter?: string) => request<ReviewTaskOut[]>(`/reviews${statusFilter ? `?status_filter=${statusFilter}` : ''}`),
  approveReview: (id: string, reviewer: string, notes?: string) =>
    request<ReviewTaskOut>(`/reviews/${id}/approve`, { method: 'POST', body: JSON.stringify({ reviewer, notes }) }),
  correctReview: (id: string, ontology_id: string, reviewer: string, notes?: string) =>
    request<ReviewTaskOut>(`/reviews/${id}/correct`, { method: 'POST', body: JSON.stringify({ ontology_id, reviewer, notes }) }),

  getMetrics: () => request<DashboardMetrics>('/metrics'),

  listJobs: () => request<IngestionJobOut[]>('/ingestion/jobs'),
  getJob: (id: string) => request<IngestionJobDetail>(`/ingestion/jobs/${id}`),

  getScalePresets: () => request<{ document_count_presets: (number | string)[]; default_worker_count: number }>('/scale-simulator/presets'),
  runScaleSimulation: (documentCount: string, workerCount: number) =>
    request<ScaleSimulationResult>(`/scale-simulator?document_count=${encodeURIComponent(documentCount)}&worker_count=${workerCount}`),
}
