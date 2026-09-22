import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import type { OntologyTreeNode, ReviewTaskOut } from '../api/types'
import { Card, CardHeader, EmptyState } from '../components/ui/Card'
import { ConfidenceBadge, Pill } from '../components/ui/Badge'

function collectLeaves(node: OntologyTreeNode, acc: { id: string; label: string }[] = []) {
  if (node.children.length === 0 && node.level === 'type') {
    acc.push({ id: node.id, label: node.path.join(' / ') })
  }
  node.children.forEach((c) => collectLeaves(c, acc))
  return acc
}

export function ReviewQueue() {
  const { data: reviews, loading, refetch } = useApi(() => api.listReviews(), [])
  const { data: tree } = useApi(() => api.getOntologyTree(), [])
  const [selected, setSelected] = useState<ReviewTaskOut | null>(null)
  const [correctionId, setCorrectionId] = useState('')
  const [notes, setNotes] = useState('')
  const [reviewer, setReviewer] = useState('demo-reviewer')
  const [busy, setBusy] = useState(false)

  const leaves = useMemo(() => (tree ? collectLeaves(tree) : []), [tree])
  const pending = reviews?.filter((r) => r.status === 'PENDING') ?? []
  const resolved = reviews?.filter((r) => r.status !== 'PENDING') ?? []

  async function approve() {
    if (!selected) return
    setBusy(true)
    try {
      await api.approveReview(selected.id, reviewer, notes || undefined)
      setSelected(null)
      refetch()
    } finally {
      setBusy(false)
    }
  }

  async function correct() {
    if (!selected || !correctionId) return
    setBusy(true)
    try {
      await api.correctReview(selected.id, correctionId, reviewer, notes || undefined)
      setSelected(null)
      setCorrectionId('')
      refetch()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Review Queue</h1>
        <p className="text-sm text-[var(--text-secondary)]">Human-in-the-loop for classifications below the confidence threshold</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Pending" subtitle={`${pending.length} awaiting review`} />
          {loading ? (
            <p className="p-5 text-sm text-[var(--text-muted)]">Loading…</p>
          ) : !pending.length ? (
            <EmptyState title="Review queue is empty" description="Every document cleared the confidence threshold automatically." />
          ) : (
            <ul className="divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
              {pending.map((r) => (
                <li key={r.id}>
                  <button onClick={() => setSelected(r)} className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-[var(--surface-2)]" style={{ backgroundColor: selected?.id === r.id ? 'var(--surface-2)' : undefined }}>
                    <span className="truncate">{r.document_filename}</span>
                    <ConfidenceBadge value={(r.original_prediction.confidence as number) ?? null} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="lg:col-span-2">
          {!selected ? (
            <Card>
              <EmptyState title="Select a document to review" />
            </Card>
          ) : (
            <Card>
              <CardHeader title={selected.document_filename} subtitle={selected.reason} />
              <div className="space-y-4 p-5">
                <div>
                  <p className="text-xs font-medium text-[var(--text-muted)]">Model prediction</p>
                  <p className="mt-1 text-sm">
                    {String(selected.original_prediction.document_type)} / {String(selected.original_prediction.document_subtype ?? '—')} ·{' '}
                    <Pill>{String(selected.original_prediction.ontology_id ?? 'unclassified')}</Pill>
                  </p>
                </div>

                <div>
                  <label className="text-xs font-medium text-[var(--text-muted)]">Reviewer</label>
                  <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} className="mt-1 block w-full rounded-md border bg-transparent px-3 py-1.5 text-sm" style={{ borderColor: 'var(--border)' }} />
                </div>

                <div>
                  <label className="text-xs font-medium text-[var(--text-muted)]">Notes</label>
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="mt-1 block w-full rounded-md border bg-transparent px-3 py-1.5 text-sm" style={{ borderColor: 'var(--border)' }} />
                </div>

                <div className="flex flex-wrap items-center gap-2 border-t pt-4" style={{ borderColor: 'var(--border)' }}>
                  <button disabled={busy} onClick={approve} className="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50" style={{ backgroundColor: 'var(--status-good)' }}>
                    Accept prediction
                  </button>
                  <select value={correctionId} onChange={(e) => setCorrectionId(e.target.value)} className="rounded-md border bg-transparent px-2 py-2 text-sm" style={{ borderColor: 'var(--border)' }}>
                    <option value="">Change classification to…</option>
                    {leaves.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                  <button disabled={busy || !correctionId} onClick={correct} className="rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-50" style={{ borderColor: 'var(--border)' }}>
                    Save correction
                  </button>
                </div>
              </div>
            </Card>
          )}

          {resolved.length > 0 && (
            <Card className="mt-4">
              <CardHeader title="Resolved" subtitle="Full audit trail: original prediction vs. human correction" />
              <ul className="divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
                {resolved.map((r) => (
                  <li key={r.id} className="px-5 py-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{r.document_filename}</span>
                      <Pill tone={r.status === 'CORRECTED' ? 'warning' : 'good'}>{r.status}</Pill>
                    </div>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      predicted: {String(r.original_prediction.ontology_id ?? '—')}
                      {r.human_correction && <> → corrected to: {String(r.human_correction.ontology_id)}</>} · by {r.reviewer} at {r.resolved_at && new Date(r.resolved_at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
