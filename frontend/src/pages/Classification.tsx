import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { Card, CardHeader, EmptyState } from '../components/ui/Card'
import { ConfidenceBadge, DomainBadge, Pill } from '../components/ui/Badge'

export function Classification() {
  const { data: docs } = useApi(() => api.listDocuments({ limit: 200 }), [])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: detail } = useApi(() => (selectedId ? api.getDocument(selectedId) : Promise.resolve(null)), [selectedId])

  useEffect(() => {
    if (!selectedId && docs?.items.length) setSelectedId(docs.items[0].id)
  }, [docs, selectedId])

  const current = detail?.classification_history.find((c) => c.is_current)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Classification Intelligence</h1>
        <p className="text-sm text-[var(--text-secondary)]">Why the system believes a document is what it says it is</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Documents" />
          <ul className="max-h-[600px] divide-y overflow-y-auto text-sm" style={{ borderColor: 'var(--border)' }}>
            {docs?.items.map((d) => (
              <li key={d.id}>
                <button
                  onClick={() => setSelectedId(d.id)}
                  className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-[var(--surface-2)]"
                  style={{ backgroundColor: selectedId === d.id ? 'var(--surface-2)' : undefined }}
                >
                  <span className="truncate">{d.filename}</span>
                  <ConfidenceBadge value={d.classification_confidence} />
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <div className="space-y-4 lg:col-span-2">
          {!detail || !current ? (
            <Card>
              <EmptyState title="Select a document" />
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader title={detail.document.filename} subtitle={`Ontology: ${detail.document.ontology_path?.join(' / ') ?? 'unclassified'}`} />
                <div className="grid grid-cols-2 gap-5 p-5 sm:grid-cols-3">
                  <LabeledValue label="File Type" value={detail.document.extension.replace('.', '').toUpperCase()} />
                  <LabeledValue label="Semantic Type" value={current.document_subtype?.replace(/_/g, ' ') ?? '—'} />
                  <LabeledValue label="Domain" value={<DomainBadge domain={current.domain} />} />
                  <LabeledValue label="Subtype" value={current.document_type.replace(/_/g, ' ')} />
                  <LabeledValue label="Confidence" value={<ConfidenceBadge value={current.confidence} action={current.confidence_action} />} />
                  <LabeledValue label="Method" value={<Pill tone={current.method === 'human' ? 'warning' : 'neutral'}>{current.method}</Pill>} />
                </div>
              </Card>

              <Card>
                <CardHeader title="Ontology Path" />
                <div className="flex items-center gap-2 p-5 text-sm">
                  {(detail.document.ontology_path ?? ['Unclassified']).map((seg, i, arr) => (
                    <span key={i} className="flex items-center gap-2">
                      <span className="rounded-md px-2 py-1" style={{ backgroundColor: 'var(--surface-2)' }}>
                        {seg}
                      </span>
                      {i < arr.length - 1 && <span className="text-[var(--text-muted)]">/</span>}
                    </span>
                  ))}
                </div>
              </Card>

              <Card>
                <CardHeader title="Signals" subtitle={`classifier_version=${detail.document.classifier_version} · ontology_version=${detail.document.ontology_version}`} />
                <ul className="space-y-1.5 p-5 text-sm">
                  {current.reasoning_signals.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span style={{ color: 'var(--status-good)' }}>✓</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function LabeledValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <div className="mt-1 text-sm font-medium capitalize">{value}</div>
    </div>
  )
}
