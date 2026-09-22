import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { Card, CardHeader, StatTile } from '../components/ui/Card'
import { HorizontalBarList } from '../components/charts/HorizontalBarList'
import { OrdinalBarChart } from '../components/charts/OrdinalBarChart'
import { domainColor, cssVar } from '../lib/colors'
import { useAppState } from '../state/AppContext'

const CONFIDENCE_ORDER = ['0.0-0.5', '0.5-0.7', '0.7-0.9', '0.9-1.0']

export function Dashboard() {
  const { data: metrics, loading } = useApi(() => api.getMetrics(), [])
  const { health } = useAppState()

  const domainItems = useMemo(
    () => Object.entries(metrics?.documents_by_domain ?? {}).map(([label, value]) => ({ label, value, color: domainColor(label) })),
    [metrics],
  )
  const typeItems = useMemo(
    () =>
      Object.entries(metrics?.documents_by_type ?? {})
        .sort((a, b) => b[1] - a[1])
        .map(([label, value]) => ({ label: label.replace(/_/g, ' '), value })),
    [metrics],
  )
  const fileTypeItems = useMemo(
    () =>
      Object.entries(metrics?.documents_by_file_type ?? {})
        .sort((a, b) => b[1] - a[1])
        .map(([label, value]) => ({ label, value })),
    [metrics],
  )
  const confidenceData = useMemo(
    () =>
      CONFIDENCE_ORDER.map((label, i) => ({
        label,
        value: metrics?.confidence_distribution?.[label] ?? 0,
        color: [cssVar('--status-critical'), cssVar('--status-serious'), cssVar('--status-warning'), cssVar('--status-good')][i],
      })),
    [metrics],
  )

  if (loading || !metrics) {
    return <p className="text-sm text-[var(--text-muted)]">Loading dashboard…</p>
  }

  const routing = metrics.cost_aware_routing

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {health?.demo_mode ? 'Demo Mode — deterministic pipeline, no external LLM calls.' : 'LLM Mode active.'}
          </p>
        </div>
        <Link to="/ingestion" className="rounded-lg px-4 py-2 text-sm font-medium text-white" style={{ backgroundColor: 'var(--series-1)' }}>
          Ingest documents
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatTile label="Documents Ingested" value={metrics.documents_ingested} />
        <StatTile label="Processing Success Rate" value={`${(metrics.processing_success_rate * 100).toFixed(0)}%`} tone="var(--status-good)" />
        <StatTile label="Requiring Review" value={metrics.documents_requiring_review} tone="var(--status-serious)" />
        <StatTile label="Avg. Classification Confidence" value={`${(metrics.average_classification_confidence * 100).toFixed(0)}%`} />
        <StatTile label="Chunks / Embeddings" value={`${metrics.chunks_created} / ${metrics.embeddings_generated}`} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Documents by Ontology Domain" subtitle="Rolled up from each document's controlled classification" />
          <div className="p-5">
            <HorizontalBarList items={domainItems} />
          </div>
        </Card>
        <Card>
          <CardHeader title="Documents by File Type" subtitle="Detected deterministically at ingestion, before any classification" />
          <div className="p-5">
            <HorizontalBarList items={fileTypeItems} />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Confidence Distribution" subtitle="AUTO_ACCEPT ≥0.90 · SECONDARY_VALIDATION 0.70–0.89 · REVIEW_REQUIRED <0.70" />
          <div className="p-5">
            <OrdinalBarChart data={confidenceData} />
          </div>
        </Card>
        <Card>
          <CardHeader title="Documents by Semantic Type" subtitle="Business type inferred by the classifier, not the file format" />
          <div className="p-5">
            <HorizontalBarList items={typeItems} />
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Cost-Aware Processing Routing"
          subtitle="Most documents never reach an LLM — see docs/decisions.md ADR-002"
        />
        <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-3">
          <RoutingTile label="Deterministic (rules + embeddings)" value={routing.rule_or_embedding} total={metrics.documents_ingested} color="var(--status-good)" />
          <RoutingTile label="LLM-adjudicated" value={routing.llm_adjudicated} total={metrics.documents_ingested} color="var(--status-info)" />
          <RoutingTile label="Human-corrected" value={routing.human_corrected} total={metrics.documents_ingested} color="var(--status-warning)" />
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Duplicate Documents" value={metrics.duplicate_documents} />
        <StatTile label="Failed Documents" value={metrics.failed_documents} tone={metrics.failed_documents > 0 ? 'var(--status-critical)' : undefined} />
        <StatTile label="Indexed Documents" value={metrics.indexed_documents} />
        <StatTile label="Documents by Status" value={Object.keys(metrics.documents_by_status).length + ' states'} />
      </div>
    </div>
  )
}

function RoutingTile({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total ? Math.round((value / total) * 100) : 0
  return (
    <div>
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1 text-xl font-semibold" style={{ color }}>
        {value} <span className="text-sm font-normal text-[var(--text-muted)]">({pct}%)</span>
      </p>
    </div>
  )
}
