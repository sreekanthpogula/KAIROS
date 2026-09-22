import type { ReactNode } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Card, CardHeader } from '../components/ui/Card'
import { Pill } from '../components/ui/Badge'
import { PRODUCTION_READINESS } from '../data/productionReadiness'

export function SystemHealth() {
  const { data: health, loading } = useApi(() => api.health(), [])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">System Health</h1>
        <p className="text-sm text-[var(--text-secondary)]">Live configuration and an honest assessment of what's POC vs. production-ready</p>
      </div>

      <Card>
        <CardHeader title="API Health" />
        {loading || !health ? (
          <p className="p-5 text-sm text-[var(--text-muted)]">Checking…</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-3">
            <Field label="Status" value={<Pill tone={health.status === 'ok' ? 'good' : 'critical'}>{health.status}</Pill>} />
            <Field label="Mode" value={<Pill tone={health.demo_mode ? 'warning' : 'info'}>{health.demo_mode ? 'Demo Mode' : 'LLM Mode'}</Pill>} />
            <Field label="Database" value={<span className="capitalize">{health.database}</span>} />
            <Field label="Embedding provider" value={health.embedding_provider} />
            <Field label="Vector backend" value={health.vector_backend} />
            <Field label="LLM mode active" value={health.llm_mode ? 'yes' : 'no'} />
          </div>
        )}
        {health?.startup_error && (
          <div className="border-t px-5 py-4 text-sm" style={{ borderColor: 'var(--border)', color: 'var(--status-critical)' }}>
            <p className="font-medium">Startup failed — API is running in a degraded state:</p>
            <p className="mt-1 font-mono text-xs">{health.startup_error}</p>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Production Readiness Scorecard" subtitle="This POC is NOT production-ready — this table is deliberately honest about the gap" />
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs text-[var(--text-muted)]">
              <th className="px-5 py-2 font-medium">Category</th>
              <th className="px-5 py-2 font-medium">POC Implementation</th>
              <th className="px-5 py-2 font-medium">Production Next Step</th>
            </tr>
          </thead>
          <tbody>
            {PRODUCTION_READINESS.map((row) => (
              <tr key={row.category} className="border-t align-top" style={{ borderColor: 'var(--border)' }}>
                <td className="px-5 py-3 font-medium">{row.category}</td>
                <td className="px-5 py-3 text-[var(--text-secondary)]">{row.poc}</td>
                <td className="px-5 py-3 text-[var(--text-secondary)]">{row.production}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <div className="mt-1 text-sm font-medium">{value}</div>
    </div>
  )
}
