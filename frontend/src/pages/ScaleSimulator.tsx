import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import type { ScaleSimulationResult } from '../api/types'
import { Card, CardHeader, StatTile } from '../components/ui/Card'
import { Pill } from '../components/ui/Badge'

export function ScaleSimulator() {
  const { data: presets } = useApi(() => api.getScalePresets(), [])
  const [documentCount, setDocumentCount] = useState('15')
  const [workerCount, setWorkerCount] = useState(8)
  const [result, setResult] = useState<ScaleSimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [showNotes, setShowNotes] = useState(false)

  async function run() {
    setLoading(true)
    try {
      setResult(await api.runScaleSimulation(documentCount, workerCount))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Scale Simulator</h1>
        <p className="text-sm text-[var(--text-secondary)]">How this same architecture evolves from 15 documents to 1TB — nothing here is actually generated or processed</p>
      </div>

      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs font-medium text-[var(--text-muted)]">Document count</label>
            <div className="mt-1 flex gap-1.5">
              {(presets?.document_count_presets ?? [15, 1000, 10000, 100000, '1TB']).map((p) => (
                <button
                  key={String(p)}
                  onClick={() => setDocumentCount(String(p))}
                  className="rounded-md border px-3 py-1.5 text-sm font-medium"
                  style={{ borderColor: 'var(--border)', backgroundColor: documentCount === String(p) ? 'var(--series-1)' : 'transparent', color: documentCount === String(p) ? 'white' : 'var(--text-primary)' }}
                >
                  {typeof p === 'number' ? p.toLocaleString() : p}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--text-muted)]">Worker count</label>
            <input
              type="number"
              min={1}
              max={256}
              value={workerCount}
              onChange={(e) => setWorkerCount(Number(e.target.value))}
              className="mt-1 block w-24 rounded-md border bg-transparent px-3 py-1.5 text-sm"
              style={{ borderColor: 'var(--border)' }}
            />
          </div>
          <button onClick={run} disabled={loading} className="rounded-lg px-5 py-2 text-sm font-medium text-white" style={{ backgroundColor: 'var(--series-1)' }}>
            {loading ? 'Simulating…' : 'Run Simulation'}
          </button>
        </div>
      </Card>

      {result && (
        <>
          <div className="flex items-center gap-2">
            <Pill tone="warning">SIMULATED — not actually processed</Pill>
            <button onClick={() => setShowNotes((s) => !s)} className="text-xs text-[var(--text-muted)] hover:underline">
              {showNotes ? 'hide' : 'show'} reference sources
            </button>
          </div>

          {showNotes && (
            <Card className="p-4 text-xs text-[var(--text-secondary)]">
              <ul className="list-disc space-y-1.5 pl-4">
                {Object.values(result.reference_notes).map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            </Card>
          )}

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatTile label="Estimated Storage" value={result.storage.estimated_total_size_gb >= 1024 ? `${result.storage.estimated_total_size_tb} TB` : `${result.storage.estimated_total_size_gb} GB`} />
            <StatTile label="Estimated Chunks" value={result.volume.estimated_chunks.toLocaleString()} />
            <StatTile label="Estimated Embeddings" value={result.volume.estimated_embeddings.toLocaleString()} />
            <StatTile label="Estimated Processing Time" value={`${result.processing.estimated_processing_hours}h`} hint={`${result.processing.docs_per_worker_per_hour} docs/worker/hr × ${workerCount} workers`} />
          </div>

          <Card>
            <CardHeader title="Cost-Aware Routing at Scale" subtitle={result.cost_aware_routing.source} />
            <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-3">
              <RoutingStat label="Auto-accepted (deterministic)" pct={result.cost_aware_routing.auto_deterministic_pct} count={documentCount} color="var(--status-good)" />
              <RoutingStat label="LLM band" pct={result.cost_aware_routing.llm_adjudicated_pct} count={documentCount} color="var(--status-info)" />
              <RoutingStat label="Human review" pct={result.cost_aware_routing.human_review_pct} count={documentCount} color="var(--status-warning)" />
            </div>
          </Card>

          <Card>
            <CardHeader title="Production Architecture" subtitle="Same components, distributed — see docs/production-scaling.md" />
            <div className="overflow-x-auto p-5">
              <div className="flex min-w-max items-center gap-2">
                {result.architecture_stages.map((stage, i) => (
                  <div key={stage} className="flex items-center gap-2">
                    <div className="rounded-lg border px-3 py-2 text-xs font-medium" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface-2)' }}>
                      {stage}
                    </div>
                    {i < result.architecture_stages.length - 1 && <span className="text-[var(--text-muted)]">→</span>}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

function RoutingStat({ label, pct, count, color }: { label: string; pct: number; count: string; color: string }) {
  const n = Math.round(parseFloat(count.replace(/[^\d.]/g, '') || '0') * pct) || 0
  return (
    <div>
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1 text-xl font-semibold" style={{ color }}>
        {(pct * 100).toFixed(0)}%
      </p>
      <p className="text-xs text-[var(--text-muted)]">≈ {n.toLocaleString()} documents</p>
    </div>
  )
}
